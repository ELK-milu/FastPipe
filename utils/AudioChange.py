from io import BytesIO

import soundfile as sf
import numpy as np
import resampy

def convert_audio_to_wav(audio_bytes: bytes,set_sample_rate: int) -> bytes:
    """将任意音频字节流转换为标准WAV格式的字节流

    参数：
        audio_bytes: 输入的原始音频字节流

    返回：
        bytes: 标准化后的WAV格式字节流（单声道/16kHz/16位）
    """
    # 从字节流加载音频（自动识别格式）
    try:
        with BytesIO(audio_bytes) as input_stream, BytesIO() as output_stream:
            stream, sample_rate = sf.read(input_stream)

            if sample_rate == set_sample_rate:
                return audio_bytes

            stream = stream.astype(np.float32)

            if stream.ndim > 1:
                stream = stream[:, 0]

            if stream.shape[0] > 0:
                stream = resampy.resample(x=stream, sr_orig=sample_rate, sr_new=set_sample_rate)

            sf.write(output_stream, stream, samplerate=set_sample_rate,
                     subtype='PCM_16', format='WAV', closefd=False)
            return output_stream.getvalue()
    except Exception as e:
        return audio_bytes

