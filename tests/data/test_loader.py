"""数据加载器测试"""

import json

import pytest

from src.data.loader import load_jobs


class TestLoadJobs:
    def test_load_plain_array(self, tmp_path):
        """纯 Job 数组"""
        data = [
            {
                "jobName": "数据分析师",
                "salaryDesc": "20-30K",
                "cityName": "上海",
                "skills": ["Python"],
            },
        ]
        fp = tmp_path / "jobs.json"
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        jobs = load_jobs(str(fp))
        assert len(jobs) == 1
        assert jobs[0].job_name == "数据分析师"

    def test_load_boss_cli_envelope(self, tmp_path):
        """boss-cli envelope 格式: {ok, data: {jobList}}"""
        data = {
            "ok": True,
            "data": {
                "jobList": [
                    {"jobName": "产品经理", "brandName": "字节跳动", "skills": ["产品经理"]},
                ],
            },
        }
        fp = tmp_path / "jobs.json"
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        jobs = load_jobs(str(fp))
        assert len(jobs) == 1
        assert jobs[0].job_name == "产品经理"

    def test_load_boss_cli_flat_data(self, tmp_path):
        """boss-cli envelope 但 data 直接是数组"""
        data = {
            "ok": True,
            "data": [
                {"jobName": "测试", "skills": []},
            ],
        }
        fp = tmp_path / "jobs.json"
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        jobs = load_jobs(str(fp))
        assert len(jobs) == 1

    def test_load_single_job(self, tmp_path):
        """单个 Job 对象"""
        data = {"jobName": "工程师", "skills": ["Python"]}
        fp = tmp_path / "job.json"
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        jobs = load_jobs(str(fp))
        assert len(jobs) == 1
        assert jobs[0].job_name == "工程师"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="不存在"):
            load_jobs("/nonexistent/path.json")

    def test_invalid_json(self, tmp_path):
        fp = tmp_path / "bad.json"
        fp.write_text("not json{{{", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_jobs(str(fp))

    def test_unknown_structure(self, tmp_path):
        data = {"foo": "bar"}
        fp = tmp_path / "weird.json"
        fp.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="无法识别"):
            load_jobs(str(fp))

    def test_default_fields(self, tmp_path):
        """缺失可选字段时使用默认值"""
        data = [{"jobName": "极简岗位"}]
        fp = tmp_path / "minimal.json"
        fp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        jobs = load_jobs(str(fp))
        assert jobs[0].salary_desc == ""
        assert jobs[0].skills == []
        assert jobs[0].city_name == ""
