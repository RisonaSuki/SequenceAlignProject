# accounts/tasks.py

from __future__ import absolute_import, unicode_literals
from celery import shared_task, current_task
from .models import AlignmentTask
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import Phylo
from io import StringIO
import os
import logging
from django.conf import settings
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from Bio.Phylo.TreeConstruction import DistanceTreeConstructor, DistanceCalculator
from Bio import AlignIO
import requests
import time

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_alignment_task(self, task_id):
    try:
        logger.info(f"开始处理比对任务：{task_id}")
        task = AlignmentTask.objects.get(id=task_id)
        sequence_file = task.sequence.file.path

        # 确保文件路径是绝对路径
        if not os.path.isabs(sequence_file):
            sequence_file = os.path.join(settings.BASE_DIR, sequence_file)

        # 读取用户上传的序列（确保是FASTA格式）
        with open(sequence_file, 'r') as f:
            query_sequence = f.read()
        logger.info(f"读取到的查询序列")

        # 检查序列是否为空
        if not query_sequence.strip():
            raise ValueError("序列文件为空，请提供有效的序列。")

        # 调用远程BLAST服务
        logger.info("开始调用远程BLAST服务")
        result_handle = NCBIWWW.qblast("blastn", "nt", query_sequence)
        logger.info("BLAST查询完成")

        # 将结果保存到临时文件
        result_filename = f'alignment_result_{task.id}.xml'
        result_dir = os.path.join(settings.MEDIA_ROOT, 'alignment_results')
        os.makedirs(result_dir, exist_ok=True)
        result_path = os.path.join(result_dir, result_filename)

        with open(result_path, 'w') as result_file:
            result_file.write(result_handle.read())

        result_handle.close()

        # 解析BLAST结果并生成可视化数据
        with open(result_path, 'r') as result_file:
            blast_record = NCBIXML.read(result_file)

        # 绘制比对结果（例如，得分分布图）
        scores = [alignment.hsps[0].score for alignment in blast_record.alignments]
        plt.figure()
        plt.hist(scores, bins=20)
        plt.title('Score Distribution')
        plt.xlabel('Score')
        plt.ylabel('Frequency')

        # 保存图像
        plot_filename = f'score_distribution_{task.id}.png'
        plot_path = os.path.join(result_dir, plot_filename)
        plt.savefig(plot_path)
        plt.close()

        def clean_sequence(sequence):
            return ''.join(filter(lambda x: x in 'ATCGNatcgn-', sequence))

        def clean_sequence(sequence):
            return ''.join(filter(lambda x: x in 'ATCGNatcgn-', sequence))

        sequences = []
        for alignment in blast_record.alignments:
            for hsp in alignment.hsps:
                seq_title = f">{alignment.accession}"
                seq_sequence = clean_sequence(hsp.sbjct.replace('-', ''))
                sequences.append(f"{seq_title}\n{seq_sequence}")
                break  # 每个 alignment 只取第一个 HSP
            if len(sequences) >= 10:
                break  # 只取前 10 个比对结果

        # 将查询序列添加到序列列表中
        clean_query_sequence = clean_sequence(query_sequence.replace('\n', '').replace('\r', ''))
        query_seq_record = f">Query\n{clean_query_sequence}"
        sequences.insert(0, query_seq_record)

        # 准备多序列比对的序列数据
        msa_input = '\n'.join(sequences)

        # 调用EMBL-EBI MAFFT在线API进行多序列比对
        logger.info("开始调用EMBL-EBI MAFFT在线API进行多序列比对")

        # 提交比对任务
        submit_url = 'https://www.ebi.ac.uk/Tools/services/rest/mafft/run'
        params = {
            'email': 'hm.zhanghit@gmail.com',
            'stype': 'dna',
            'sequence': msa_input
        }
        response = requests.post(submit_url, data=params)
        if response.status_code != 200:
            error_message = response.text
            raise Exception(f"MAFFT API请求失败，状态码：{response.status_code}，错误信息：{error_message}")

        job_id = response.text.strip()
        logger.info(f"比对任务提交成功，任务ID：{job_id}")

        # 轮询任务状态，直到完成
        status_url = f'https://www.ebi.ac.uk/Tools/services/rest/mafft/status/{job_id}'
        result_base_url = f'https://www.ebi.ac.uk/Tools/services/rest/mafft/result/{job_id}'

        while True:
            status_response = requests.get(status_url)
            status = status_response.text.strip()
            logger.info(f"MAFFT比对任务状态：{status}")
            if status == 'FINISHED':
                break
            elif status in ['ERROR', 'FAILURE', 'NOT_FOUND']:
                raise Exception(f"MAFFT比对任务失败，状态：{status}")
            else:
                time.sleep(5)  # 等待5秒后再次查询

        # 获取可用的结果类型
        types_url = f'https://www.ebi.ac.uk/Tools/services/rest/mafft/resulttypes/{job_id}'
        types_response = requests.get(types_url)
        if types_response.status_code != 200:
            error_message = types_response.text
            raise Exception(f"获取结果类型失败，状态码：{types_response.status_code}，错误信息：{error_message}")

        logger.info("可用的结果类型：")
        logger.info(types_response.text)

        # 假设结果类型为 'out'
        result_url = f'{result_base_url}/out'

        # 获取比对结果
        result_response = requests.get(result_url)
        if result_response.status_code != 200:
            error_message = result_response.text
            raise Exception(f"获取比对结果失败，状态码：{result_response.status_code}，错误信息：{error_message}")

        msa_data = result_response.text

        # 保存比对结果到文件
        msa_filename = f'msa_{task.id}.fasta'
        msa_path = os.path.join(result_dir, msa_filename)
        with open(msa_path, 'w') as msa_file:
            msa_file.write(msa_data)

        # 读取多序列比对结果
        alignment = AlignIO.read(msa_path, 'fasta')

        # 计算距离矩阵
        calculator = DistanceCalculator('identity')
        dm = calculator.get_distance(alignment)

        # 构建进化树
        constructor = DistanceTreeConstructor()
        tree = constructor.nj(dm)

        # 绘制进化树
        tree_filename = f'phylogenetic_tree_{task.id}.png'
        tree_path = os.path.join(result_dir, tree_filename)
        Phylo.draw(tree, do_show=False)
        plt.savefig(tree_path)
        plt.close()

        # 更新任务模型
        task.tree_file.name = os.path.join('alignment_results', tree_filename)
        task.save()

        # 更新任务状态和结果文件
        task.status = 'SUCCESS'
        task.result_file.name = os.path.join('alignment_results', result_filename)
        task.save()
        logger.info(f"比对任务 {task_id} 完成")


    except Exception as e:
        logger.exception(f"比对任务 {task_id} 出现错误：{e}")
        task.status = 'FAILURE'
        task.save()
        raise self.retry(exc=e, countdown=60, max_retries=3)
