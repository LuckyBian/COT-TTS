from dataclasses import dataclass
from typing import Tuple

import numpy.typing as npt

from modules.models.BaseZooModel import BaseZooModel

NP_AUDIO = Tuple[int, npt.NDArray]


@dataclass(frozen=True, repr=False, eq=False)
class TranscribeResult:
    text: str
    segments: list

    info: dict


class STTModel(BaseZooModel):

    def __init__(self, model_id: str) -> None:
        super().__init__(model_id=model_id)

    def transcribe_and_diarize(self, audio: NP_AUDIO) -> TranscribeResult:
        raise NotImplementedError()
