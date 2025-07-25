import os
import time
import uuid
import pytest
import requests

@pytest.mark.e2e
class TestComplaintReportGeneration:
    def test_complaint_csv_report_generation(self, authenticated_session, api_base_url, cleanup_e2e_data):
        """
        自动化测试：用complaint_raw_data.csv数据源，自动化生成报告并校验
        """
        # 1. 上传数据源
        csv_path = os.path.join(
            os.path.dirname(__file__),
            "../test_data/csv_data/complaint_raw_data.csv"
        )
        with open(csv_path, "rb") as f:
            resp = authenticated_session.post(
                f"{api_base_url}/data-sources/upload",
                files={"file": f},
                data={"name": f"投诉数据源_{uuid.uuid4().hex[:6]}"}
            )
        assert resp.status_code == 200 or resp.status_code == 201, resp.text
        ds_data = resp.json()
        data_source_id = ds_data["data"]["id"] if "data" in ds_data and "id" in ds_data["data"] else ds_data["id"]

        # 2. 创建模板
        template_content = (
            "投诉数据分析报告\n\n"
            "1. 总投诉数：{{count: 总投诉数}}\n"
            "2. 平均响应时间（分钟）：{{avg_response_time: 平均响应时间}}\n"
            "3. 24小时内解决率：{{rate_24h: 24小时内解决率}}\n"
            "4. 平均满意度分数：{{avg_satisfaction: 平均满意度}}\n"
            "5. 区域投诉分布：\n{{region_stats: 区域投诉统计}}\n"
        )
        resp = authenticated_session.post(
            f"{api_base_url}/templates/",
            json={
                "name": f"投诉报告模板_{uuid.uuid4().hex[:6]}",
                "description": "自动化投诉报告模板",
                "template_type": "text",
                "content": template_content
            }
        )
        assert resp.status_code == 200 or resp.status_code == 201, resp.text
        tpl_data = resp.json()
        template_id = tpl_data["data"]["id"] if "data" in tpl_data and "id" in tpl_data["data"] else tpl_data["id"]

        # 3. 创建任务
        resp = authenticated_session.post(
            f"{api_base_url}/tasks/",
            json={
                "name": f"投诉报告任务_{uuid.uuid4().hex[:6]}",
                "template_id": template_id,
                "data_source_id": data_source_id
            }
        )
        assert resp.status_code == 200 or resp.status_code == 201, resp.text
        task_data = resp.json()
        task_id = task_data["data"]["id"] if "data" in task_data and "id" in task_data["data"] else task_data["id"]

        # 4. 生成报告
        resp = authenticated_session.post(
            f"{api_base_url}/reports/generate",
            json={
                "template_id": template_id,
                "data_source_id": data_source_id
            }
        )
        assert resp.status_code == 200 or resp.status_code == 201, resp.text
        gen_data = resp.json()
        assert gen_data["success"]
        report_task_id = gen_data["data"]["task_id"] if "data" in gen_data and "task_id" in gen_data["data"] else gen_data["data"].get("report_id")

        # 5. 轮询报告状态
        max_wait = 60
        interval = 3
        waited = 0
        report_ready = False
        while waited < max_wait:
            resp = authenticated_session.get(f"{api_base_url}/reports")
            assert resp.status_code == 200, resp.text
            reports = resp.json()["data"]["items"] if "data" in resp.json() and "items" in resp.json()["data"] else resp.json()
            found = [r for r in reports if r.get("task_id") == task_id]
            if found and found[0].get("status") == "completed":
                report_ready = True
                break
            time.sleep(interval)
            waited += interval
        assert report_ready, "报告未在预期时间内生成完成" 