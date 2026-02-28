"""
rejecter.py — 리젝트 신호 관리 모듈
======================================

[역할]
    컨베이어 벨트 속도에 맞춰 "지연 리젝트"를 구현합니다.
    슬라이딩 윈도우(deque)로 불량 결과를 추적하고,
    window[-N:] 범위 안에 1이 있는 위치마다 독립적으로 신호를 발생시킵니다.

[슬라이딩 윈도우 개념]
    reject_delay_frames=10, reject_positions=3 예시:

    초기:         [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                   ↑ index 0                    ↑ index -1
                   (최신)                        (가장 오래된)

    불량 감지 후 shift 7회:
                  [0, 0, 0, 0, 0, 0, 0, 1, 0, 0]  ← index[-3] → 발사 1
    shift 8회:    [0, 0, 0, 0, 0, 0, 0, 0, 1, 0]  ← index[-2] → 발사 2
    shift 9회:    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]  ← index[-1] → 발사 3

    reject_positions = 1 → window[-1:]만 체크 → 1번 발사 (기본 동작)
    reject_positions = 3 → window[-3:] 체크 → 최대 3번 발사

[커스터마이즈 포인트]
    - reject_delay_frames : 슬라이딩 윈도우 크기 (컨베이어 딜레이)
    - reject_positions    : window[-N:] 범위 크기. 이 범위 안 각 위치에서 독립 발사
    - time_valve_on       : 밸브 열림 지속 시간 [초] (예: 0.1, 0.2, 0.3)
    - pre_valve_delay      : 리젝트 신호 ON 전 추가 대기 시간 [초]
    - camera              : BaslerCamera 인스턴스 (신호 출력에 필요)

[insert_position 활용 예시]
    # 카메라 FOV 내 제품 위치로 삽입 위치를 계산해 전달
    y_ratio = detection.y_center / frame_height  # 0.0 ~ 1.0
    pos = int(y_ratio * reject_delay_frames)
    rejecter.push(is_defect=True, insert_position=pos)
"""

import time
import threading
from collections import deque
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from camera import BaslerCamera


class Rejecter:
    """
    슬라이딩 윈도우 기반 지연 리젝트 신호 관리 클래스.

    [동작 원리]
        1. push(is_defect, insert_position)을 매 프레임 호출합니다.
        2. 윈도우를 한 칸 shift(appendleft)하고, 불량이면 insert_position에 마킹합니다.
        3. window[-reject_positions:] 범위의 각 인덱스를 체크합니다.
        4. 1이 있는 인덱스마다 독립적으로 리젝트 신호를 발사합니다.

    사용법 예시
    -----------
    rejecter = Rejecter(
        camera=cam,
        reject_delay_frames=10,   # 윈도우 크기
        reject_positions=3,       # 뒤 3칸 체크 → 불량 1개당 최대 3번 발사
        time_valve_on=0.1,
        pre_valve_delay=0.25,
    )

    # 메인 루프 안에서:
    rejecter.push(is_defect=True)                     # 기본: 맨 앞(0)에 마킹
    rejecter.push(is_defect=True, insert_position=3)  # 앞에서 4번째에 마킹
    """

    def __init__(
        self,
        camera: "BaslerCamera",
        reject_delay_frames: int = 10,
        time_valve_on: float = 0.1,
        pre_valve_delay: float = 0.25,
        reject_positions: int = 1,
    ):
        """
        Parameters
        ----------
        camera               : BaslerCamera 인스턴스 (리젝트 신호 출력용)
        reject_delay_frames  : 슬라이딩 윈도우 크기.
                               컨베이어 속도와 카메라 위치에 따라 조정하세요.
        reject_positions     : window[-N:] 범위 크기.
                               1 = 맨 뒤 1칸만 체크 (기본, 1번 발사)
                               3 = 뒤 3칸 체크 (최대 3번 발사)
        time_valve_on        : 밸브 열림 지속 시간 [초] (예: 0.1, 0.2, 0.3).
        pre_valve_delay       : 신호 발생 직전 추가 대기 시간 [초].
                               에어건 등 기계 응답 지연 보상에 사용합니다.
        """
        self.camera = camera
        self.reject_delay_frames = reject_delay_frames
        self.reject_positions = reject_positions
        self.time_valve_on = time_valve_on
        self.pre_valve_delay = pre_valve_delay

        # 슬라이딩 윈도우: 0으로 초기화, maxlen으로 크기 고정
        self._window: deque = deque(
            [0] * reject_delay_frames, maxlen=reject_delay_frames
        )
        # warm-up: delay_frames만큼 실제 데이터가 쌓인 후부터 체크
        self._push_count: int = 0

        self._lock = threading.Lock()
        self._firing_positions: set = set()  # 현재 발사 중인 인덱스 집합
        self._fire_lock = threading.Lock()   # I/O 신호 ON/OFF 경쟁 조건 방지
        self._active_fires: int = 0          # 현재 발사 중인 스레드 수

    # ------------------------------------------------------------------
    # 공개 메서드 (Public Methods)
    # ------------------------------------------------------------------

    def push(self, is_defect: bool, insert_position: int = 0) -> List[int]:
        """
        검사 결과를 슬라이딩 윈도우에 추가하고, 리젝트 조건을 확인합니다.
        매 프레임 호출해야 합니다.

        Parameters
        ----------
        is_defect       : True이면 불량, False이면 정상
        insert_position : 윈도우에서 불량을 마킹할 인덱스 (기본 0=맨 앞).
                          카메라 FOV 내 제품 위치를 계산해 전달할 수 있습니다.

        Returns
        -------
        List[int] : 이번 호출에서 발사가 시작된 인덱스 목록 (예: [-3, -2])
        """
        fired = []
        with self._lock:
            # 1. 윈도우를 한 칸 shift: 앞에 0 추가, 맨 뒤는 자동 제거
            self._window.appendleft(0)
            self._push_count += 1

            # 2. 불량이면 지정 위치에 마킹
            if is_defect:
                self._window[insert_position] = 1

            # 3. warm-up: delay_frames 이전에는 체크하지 않음
            if self._push_count < self.reject_delay_frames:
                return fired

            # 4. window[-N:] 범위의 각 인덱스 체크 — 각각 독립 발사
            for i in range(-self.reject_positions, 0):
                if self._window[i] == 1 and i not in self._firing_positions:
                    self._firing_positions.add(i)
                    fired.append(i)
                    threading.Thread(
                        target=self._fire_reject, args=(i,), daemon=True
                    ).start()

        return fired

    def reset(self):
        """윈도우와 리젝트 상태를 초기화합니다. 라인 정지/재시작 시 호출하세요."""
        with self._lock:
            self._window = deque(
                [0] * self.reject_delay_frames, maxlen=self.reject_delay_frames
            )
            self._push_count = 0
            self._firing_positions = set()
        with self._fire_lock:
            self._active_fires = 0
        self.camera.set_reject_output(False)
        print("[Rejecter] Window reset.")

    @property
    def window_state(self) -> list:
        """현재 슬라이딩 윈도우 상태를 리스트로 반환합니다 (디버깅/UI 모니터링용)."""
        with self._lock:
            return list(self._window)

    # ------------------------------------------------------------------
    # 내부 메서드 (Internal Methods)
    # ------------------------------------------------------------------

    def _fire_reject(self, idx: int):
        """별도 스레드에서 리젝트 신호를 ON → 대기 → OFF 합니다.

        카운터 방식으로 경쟁 조건을 방지합니다:
        - 여러 스레드가 동시에 ON을 요청해도 신호는 한 번만 ON 됩니다.
        - 마지막 스레드가 끝날 때만 OFF 하므로 중간에 끊기지 않습니다.
        """
        try:
            time.sleep(self.pre_valve_delay)   # 기계 응답 딜레이 보상
            with self._fire_lock:
                self._active_fires += 1
                self.camera.set_reject_output(True)
            print(f"[Rejecter] REJECT ON (idx={idx}, {self.time_valve_on}s)")
            time.sleep(self.time_valve_on)  # 밸브 열림 지속 시간
        finally:
            with self._fire_lock:
                self._active_fires -= 1
                if self._active_fires == 0:
                    self.camera.set_reject_output(False)
                    print(f"[Rejecter] REJECT OFF (idx={idx})")
            with self._lock:
                self._firing_positions.discard(idx)
