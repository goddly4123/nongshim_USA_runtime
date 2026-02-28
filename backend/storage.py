"""
backend/storage.py — 스토리지 백엔드 추상화 (S3 준비)
=====================================================

[역할]
    이미지 저장소를 로컬 파일시스템에서 AWS S3로 전환할 수 있도록
    스토리지 추상 인터페이스와 백그라운드 동기화 워커를 제공합니다.

[현재 상태]
    - LocalStorage : 동작 확인 완료 (DataManager가 이미 로컬 저장 처리)
    - S3Storage    : 스텁 구현 (boto3 설치 후 활성화)
    - S3SyncWorker : 백그라운드 업로드 큐 구현

[S3 활성화 방법]
    1. 의존성 추가: uv add boto3
    2. 환경 변수 설정:
        export AWS_S3_BUCKET=your-bucket-name
        export AWS_REGION=ap-northeast-2  (선택)
        export AWS_ACCESS_KEY_ID=...      (또는 IAM Role 사용)
        export AWS_SECRET_ACCESS_KEY=...
    3. backend/main.py에서 _make_worker() 호출 시 on_save_callback 연결:
        from backend.storage import S3SyncWorker
        sync = S3SyncWorker(bucket="your-bucket", region="ap-northeast-2")
        sync.start()
        worker = InspectionWorker(cfg, on_save_callback=sync.enqueue)

[저장 구조 (S3)]
    s3://bucket/{line_name}/{category}/{class_name}/YYYY-MM-DD/HH/filename.jpg
"""

from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from queue import Queue, Full, Empty
from typing import List, Optional


# ── 추상 인터페이스 ──────────────────────────────────────────────────────────

class StorageBackend(ABC):
    """스토리지 백엔드 추상 클래스."""

    @abstractmethod
    def upload(self, local_path: str, remote_key: str) -> str:
        """로컬 파일을 원격 스토리지에 업로드합니다.

        Parameters
        ----------
        local_path : 업로드할 로컬 파일 경로
        remote_key : 원격 스토리지의 키/경로

        Returns
        -------
        str : 업로드된 파일의 원격 URL 또는 키
        """
        ...

    @abstractmethod
    def list_keys(self, prefix: str) -> List[str]:
        """원격 스토리지에서 prefix로 시작하는 키 목록을 반환합니다."""
        ...

    @abstractmethod
    def delete(self, remote_key: str) -> bool:
        """원격 스토리지에서 파일을 삭제합니다."""
        ...


# ── 로컬 파일시스템 (기본, DataManager와 동일 경로) ──────────────────────────

class LocalStorage(StorageBackend):
    """로컬 파일시스템 스토리지. DataManager가 이미 저장하므로 no-op에 가깝습니다."""

    def __init__(self, base_dir: str = "./data"):
        self.base_dir = os.path.abspath(base_dir)

    def upload(self, local_path: str, remote_key: str) -> str:
        # DataManager가 이미 로컬에 저장하므로 추가 작업 불필요
        return local_path

    def list_keys(self, prefix: str) -> List[str]:
        target = os.path.join(self.base_dir, prefix)
        if not os.path.isdir(target):
            return []
        result = []
        for root, _, files in os.walk(target):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, self.base_dir)
                result.append(rel)
        return result

    def delete(self, remote_key: str) -> bool:
        path = os.path.join(self.base_dir, remote_key)
        if os.path.isfile(path):
            os.remove(path)
            return True
        return False


# ── AWS S3 스토리지 (스텁 — boto3 설치 후 활성화) ───────────────────────────

class S3Storage(StorageBackend):
    """AWS S3 스토리지 백엔드.

    사용하려면 boto3 패키지가 필요합니다:
        uv add boto3
    """

    def __init__(self, bucket: str, region: str = "ap-northeast-2", prefix: str = "",
                 access_key: str = "", secret_key: str = ""):
        self.bucket = bucket
        self.region = region
        self.prefix = prefix.rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3  # noqa: PLC0415
                kwargs = {"region_name": self.region}
                if self._access_key and self._secret_key:
                    kwargs["aws_access_key_id"] = self._access_key
                    kwargs["aws_secret_access_key"] = self._secret_key
                self._client = boto3.client("s3", **kwargs)
            except ImportError:
                raise ImportError(
                    "[S3Storage] boto3 is not installed. Run: uv add boto3"
                )
        return self._client

    def _make_key(self, remote_key: str) -> str:
        if self.prefix:
            return f"{self.prefix}/{remote_key}"
        return remote_key

    def upload(self, local_path: str, remote_key: str) -> str:
        client = self._get_client()
        key = self._make_key(remote_key)
        client.upload_file(local_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def list_keys(self, prefix: str) -> List[str]:
        client = self._get_client()
        full_prefix = self._make_key(prefix)
        result = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                result.append(obj["Key"])
        return result

    def delete(self, remote_key: str) -> bool:
        client = self._get_client()
        key = self._make_key(remote_key)
        try:
            client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


# ── S3 백그라운드 동기화 워커 ────────────────────────────────────────────────

class S3SyncWorker:
    """백그라운드 스레드에서 로컬 이미지를 S3에 업로드하는 큐 워커.

    InspectionWorker의 on_save_callback에 self.enqueue를 전달하면
    이미지 저장 시마다 자동으로 S3 업로드 큐에 추가됩니다.

    사용법
    ------
    sync = S3SyncWorker(bucket="my-bucket", region="ap-northeast-2")
    sync.start()

    # InspectionWorker 생성 시:
    worker = InspectionWorker(cfg, on_save_callback=sync.enqueue)

    # 종료 시:
    sync.stop()
    """

    def __init__(
        self,
        bucket: str,
        region: str = "ap-northeast-2",
        prefix: str = "",
        access_key: str = "",
        secret_key: str = "",
        max_queue: int = 1000,
        num_workers: int = 2,
    ):
        self._storage = S3Storage(
            bucket=bucket, region=region, prefix=prefix,
            access_key=access_key, secret_key=secret_key,
        )
        self._queue: Queue = Queue(maxsize=max_queue)
        self._stop_event = threading.Event()
        self._threads: list = []
        self._num_workers = num_workers
        self._uploaded_count = 0
        self._error_count = 0
        self._enqueued_paths: set = set()
        self._enqueue_hour: str = ""

    def start(self):
        """업로드 워커 스레드를 시작합니다."""
        self._stop_event.clear()
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._upload_loop,
                name=f"s3-sync-{i}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        print(f"[S3Sync] Started {self._num_workers} upload workers "
              f"(bucket: {self._storage.bucket})")

    def stop(self):
        """업로드 워커를 종료합니다."""
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=5)
        self._threads.clear()

    @property
    def stats(self) -> dict:
        return {
            "queue_size": self._queue.qsize(),
            "uploaded": self._uploaded_count,
            "errors": self._error_count,
        }

    def enqueue(self, category: str, save_root: str, line_name: str,
                detections=None, **_kwargs):
        """on_save_callback 시그니처에 맞는 큐 추가 메서드.

        DataManager가 실제로 저장한 파일을 디렉토리 스캔으로 찾아서 큐에 넣습니다.
        (기존: datetime.now()로 파일명을 재구성 → 밀리초 차이로 경로 불일치 버그)
        """
        if detections is None:
            return
        class_name = max(detections, key=lambda d: d.confidence).label if detections else "unknown"
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        hour_str = now.strftime("%H")
        local_dir = os.path.join(save_root, category, line_name, class_name, date_str, hour_str)

        if not os.path.isdir(local_dir):
            return

        # 시간대가 바뀌면 중복 추적 셋 초기화 (메모리 관리)
        if hour_str != self._enqueue_hour:
            self._enqueued_paths.clear()
            self._enqueue_hour = hour_str

        # 디렉토리에서 아직 큐에 넣지 않은 파일을 찾아 업로드 큐에 추가
        for fname in os.listdir(local_dir):
            local_path = os.path.join(local_dir, fname)
            if local_path in self._enqueued_paths:
                continue
            if not os.path.isfile(local_path):
                continue
            self._enqueued_paths.add(local_path)
            remote_key = f"{line_name}/{category}/{class_name}/{date_str}/{hour_str}/{fname}"
            try:
                self._queue.put_nowait((local_path, remote_key))
            except Full:
                self._error_count += 1

    def _upload_loop(self):
        """워커 스레드: 큐에서 파일을 꺼내 S3에 업로드합니다."""
        while not self._stop_event.is_set():
            try:
                local_path, remote_key = self._queue.get(timeout=2.0)
            except Empty:
                continue
            if not os.path.isfile(local_path):
                continue
            try:
                self._storage.upload(local_path, remote_key)
                self._uploaded_count += 1
            except Exception as e:
                self._error_count += 1
                print(f"[S3Sync] Upload failed: {remote_key} - {e}")
