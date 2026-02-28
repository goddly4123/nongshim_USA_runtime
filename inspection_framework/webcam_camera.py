"""
webcam_camera.py — PC 웹캠 / USB 카메라 모듈 (OpenCV VideoCapture 기반)
=========================================================================

[역할]
    cv2.VideoCapture를 이용해 PC 웹캠 또는 USB 카메라와 통신합니다.
    BaslerCamera와 완전히 동일한 인터페이스를 제공하여 투명하게 교체됩니다.

[커스터마이즈 포인트]
    - camera_ip   : 웹캠 인덱스 문자열 ("0", "1", ...) 또는 RTSP URL
    - rotation    : 이미지 회전 방향 (cv2.ROTATE_* 상수 또는 None)
    - crop_region : 검사 ROI [x1, y1, x2, y2] 또는 None
"""

import cv2


class WebcamCamera:
    """
    웹캠/USB 카메라 제어 클래스. BaslerCamera와 동일한 인터페이스.

    사용법 예시
    -----------
    cam = WebcamCamera(camera_ip='0')   # 인덱스 0번 웹캠
    cam.open()

    frame, cropped, triggered = cam.grab()
    if triggered:
        cv2.imshow("preview", frame)

    cam.close()
    """

    def __init__(
        self,
        camera_ip: str,
        pfs_file: str = "",
        timeout_ms: int = 200,
        rotation=None,
        crop_region: list = None,
    ):
        """
        Parameters
        ----------
        camera_ip   : 웹캠 인덱스 문자열 ("0", "1", ...) 또는 RTSP URL 문자열
        pfs_file    : 사용하지 않음 (BaslerCamera 호환용)
        timeout_ms  : 사용하지 않음 (BaslerCamera 호환용)
        rotation    : 이미지 회전. cv2.ROTATE_90_CLOCKWISE 등 또는 None.
        crop_region : 관심영역(ROI) 좌표 [x1, y1, x2, y2]. None이면 전체 이미지 사용.
        """
        # 숫자 문자열이면 int로, 그 외(RTSP URL 등)는 str 그대로 사용
        try:
            self._source = int(camera_ip)
        except (ValueError, TypeError):
            self._source = camera_ip

        self.rotation = rotation
        self.crop_region = crop_region

        self._cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # 공개 메서드 (Public Methods)
    # ------------------------------------------------------------------

    def open(self):
        """카메라를 열고 이미지 수신을 시작합니다."""
        self._cap = cv2.VideoCapture(self._source)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"[WebcamCamera] 카메라 '{self._source}'을 열 수 없습니다. "
                "인덱스가 올바른지, 다른 프로그램이 점유 중인지 확인하세요."
            )
        print(f"[WebcamCamera] 카메라 {self._source} 열기 완료.")

    def grab(self):
        """
        이미지를 한 장 촬영합니다.

        Returns
        -------
        frame   : BGR 전체 이미지 (np.ndarray). 실패 시 None.
        cropped : crop_region이 지정된 경우 잘라낸 ROI 이미지. 없으면 frame과 동일.
        trigger : 촬영 성공 여부 (True / False)
        """
        if self._cap is None:
            raise RuntimeError("[WebcamCamera] open()을 먼저 호출하세요.")

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None, None, False

        # 회전 적용
        if self.rotation is not None:
            frame = cv2.rotate(frame, self.rotation)

        # ROI 크롭
        if self.crop_region is not None:
            x1, y1, x2, y2 = self.crop_region
            cropped = frame[y1:y2, x1:x2]
        else:
            cropped = frame

        return frame, cropped, True

    def set_trigger_delay(self, delay_us: float):
        """웹캠은 트리거 딜레이가 없으므로 아무 동작도 하지 않습니다."""
        pass

    def set_reject_output(self, state: bool):
        """웹캠은 하드웨어 리젝트 출력이 없으므로 아무 동작도 하지 않습니다."""
        pass

    def get_trigger_mode(self) -> str:
        """웹캠은 하드웨어 트리거가 없으므로 항상 'Off'를 반환합니다."""
        return "Off"

    def close(self):
        """카메라 연결을 안전하게 종료합니다."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            print(f"[WebcamCamera] 카메라 {self._source} 종료 완료.")
