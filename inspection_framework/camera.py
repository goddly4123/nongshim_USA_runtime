"""
camera.py — Basler 산업용 카메라 모듈 (pypylon 기반)
=======================================================

[역할]
    pypylon 라이브러리를 이용해 Basler GigE 카메라와 통신합니다.
    카메라 초기화, 이미지 촬영, 연결 해제를 담당합니다.

[커스터마이즈 포인트]
    - camera_ip    : 연결할 카메라의 IP 주소
    - pfs_file     : 카메라 설정 파일 경로 (.pfs)
    - rotation     : 이미지 회전 방향 (cv2.ROTATE_* 상수 또는 None)
    - crop_region  : OCR/검사 ROI (관심영역) [x1, y1, x2, y2] 또는 None
"""

import os

import cv2
import numpy as np
from pypylon import pylon


class BaslerCamera:
    """
    Basler GigE 카메라 제어 클래스.

    사용법 예시
    -----------
    cam = BaslerCamera(camera_ip='192.168.5.10', pfs_file='camera.pfs')
    cam.open()

    frame, cropped = cam.grab()   # 이미지 촬영
    if frame is not None:
        cv2.imshow("preview", frame)

    cam.close()
    """

    def __init__(
        self,
        camera_ip: str,
        pfs_file: str,
        timeout_ms: int = 200,
        rotation=None,
        crop_region: list = None,
    ):
        """
        Parameters
        ----------
        camera_ip   : 카메라 IP 주소 (예: '192.168.5.10')
        pfs_file    : 카메라 파라미터 설정 파일 경로 (예: 'acA1300.pfs')
        timeout_ms  : 이미지 수신 대기 시간 [밀리초]. 기본값 200ms.
        rotation    : 이미지 회전. cv2.ROTATE_90_CLOCKWISE 등 또는 None.
        crop_region : 관심영역(ROI) 좌표 [x1, y1, x2, y2]. None이면 전체 이미지 사용.
        """
        self.camera_ip = camera_ip
        self.pfs_file = pfs_file
        self.timeout_ms = timeout_ms
        self.rotation = rotation
        self.crop_region = crop_region  # [x1, y1, x2, y2]

        self._cam = None
        self._cameras = None
        self._converter = None

    # ------------------------------------------------------------------
    # 공개 메서드 (Public Methods)
    # ------------------------------------------------------------------

    def open(self):
        """카메라를 열고 이미지 수신을 시작합니다."""
        # .pfs 파일 존재 확인 (카메라 연결 전에 빠르게 실패)
        if not os.path.isfile(self.pfs_file):
            raise FileNotFoundError(
                f"[Camera] PFS file not found: '{self.pfs_file}'"
            )

        try:
            tlFactory = pylon.TlFactory.GetInstance()
            print(f"[Camera] Searching for camera at IP {self.camera_ip}...")
            devices = tlFactory.EnumerateDevices()
            print(f"[Camera] Found {len(devices)} device(s)")

            if len(devices) == 0:
                raise RuntimeError("[Camera] 연결된 카메라가 없습니다. 네트워크를 확인하세요.")

            # IP로 카메라 선택
            cam_info = None
            for dev_info in devices:
                if dev_info.GetIpAddress() == self.camera_ip:
                    cam_info = dev_info
                    print(f"[Camera] 카메라 발견: {cam_info.GetIpAddress()}")
                    break

            if cam_info is None:
                raise RuntimeError(f"[Camera] IP {self.camera_ip} 에 해당하는 카메라를 찾지 못했습니다.")

            self._cameras = pylon.InstantCameraArray(1)
            self._cam = self._cameras[0]
            self._cam.Attach(tlFactory.CreateDevice(cam_info))
            self._cameras.Open()

            # .pfs 파일로 카메라 파라미터 로드
            pylon.FeaturePersistence.Load(self.pfs_file, self._cam.GetNodeMap(), True)
            self._cameras.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            # BGR 8비트로 출력 포맷 설정
            self._converter = pylon.ImageFormatConverter()
            self._converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            self._converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

            print("[Camera] 카메라 열기 완료.")
        except Exception:
            # 부분 초기화된 리소스 정리 (카메라 Open 후 .pfs 로드 실패 등)
            if self._cameras is not None:
                try:
                    self._cameras.Close()
                except Exception:
                    pass
                self._cameras = None
                self._cam = None
            raise

    def grab(self):
        """
        이미지를 한 장 촬영합니다.

        Returns
        -------
        frame   : BGR 전체 이미지 (np.ndarray). 실패 시 None.
        cropped : crop_region이 지정된 경우 잘라낸 ROI 이미지. 없으면 frame과 동일.
        trigger : 촬영 성공 여부 (True / False)
        """
        if self._cameras is None:
            raise RuntimeError("[Camera] open()을 먼저 호출하세요.")

        try:
            grab_result = self._cameras.RetrieveResult(
                self.timeout_ms, pylon.TimeoutHandling_ThrowException
            )
        except pylon.TimeoutException:
            return None, None, False  # 정상적인 타임아웃 (트리거 미수신 등)
        except Exception as e:
            print(f"[Camera] Grab error: {e}")
            return None, None, False

        if not grab_result.GrabSucceeded():
            grab_result.Release()
            return None, None, False

        # 이미지 변환
        image_bgr = self._converter.Convert(grab_result).GetArray()
        grab_result.Release()

        # 회전 적용
        if self.rotation is not None:
            image_bgr = cv2.rotate(image_bgr, self.rotation)

        # ROI 크롭
        if self.crop_region is not None:
            x1, y1, x2, y2 = self.crop_region
            cropped = image_bgr[y1:y2, x1:x2]
        else:
            cropped = image_bgr

        return image_bgr, cropped, True

    def set_trigger_delay(self, delay_us: float):
        """
        카메라 트리거 딜레이를 변경합니다.

        Parameters
        ----------
        delay_us : 딜레이 [마이크로초]. 1,000,000 = 1초.
        """
        if self._cam is not None:
            try:
                self._cam.TriggerDelayAbs.SetValue(delay_us)
            except Exception as e:
                print(f"[Camera] set_trigger_delay({delay_us}) failed: {e}")

    def set_reject_output(self, state: bool):
        """
        카메라 하드웨어 출력(리젝트 신호)을 ON/OFF 합니다.

        Parameters
        ----------
        state : True = 리젝트 ON, False = 리젝트 OFF
        """
        if self._cam is not None:
            try:
                self._cam.UserOutputValue.SetValue(state)
            except Exception as e:
                print(f"[Camera] set_reject_output({state}) failed: {e}")

    def get_trigger_mode(self) -> str:
        """
        현재 트리거 모드를 반환합니다.

        Returns
        -------
        str : 'On', 'Off', 또는 'unknown'
        """
        if self._cam is None:
            return "unknown"
        try:
            return self._cam.TriggerMode.GetValue()
        except Exception:
            return "unknown"

    def close(self):
        """카메라 연결을 안전하게 종료합니다."""
        if self._cameras is not None:
            try:
                self.set_reject_output(False)  # 리젝트 신호 초기화
            except Exception:
                pass
            try:
                self._cameras.StopGrabbing()
            except Exception:
                pass
            try:
                self._cameras.Close()
            except Exception:
                pass
            self._cameras = None
            self._cam = None
            self._converter = None
            print("[Camera] 카메라 종료 완료.")
