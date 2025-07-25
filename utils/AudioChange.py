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


def convert_wav_to_pcm_simple(wav_bytes: bytes,set_sample_rate: int) -> bytes:
    """简化版WAV转PCM函数，使用固定参数

    参数：
        wav_bytes: 输入的WAV音频字节流

    返回：
        bytes: PCM格式的字节流（单声道/16kHz/16位）
    """
    try:
        with BytesIO(wav_bytes) as input_stream:
            # 读取音频数据
            audio_data, sample_rate = sf.read(input_stream, dtype='float32')

            # 转换为单声道
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]  # 取第一个声道

            # 重采样到16kHz（如果需要）
            if sample_rate != set_sample_rate:
                import resampy
                audio_data = resampy.resample(x=audio_data, sr_orig=sample_rate, sr_new=set_sample_rate)

            # 转换为16位PCM
            audio_data = np.clip(audio_data, -1.0, 1.0)
            pcm_data = (audio_data * 32767).astype(np.int16)

            return pcm_data.tobytes()

    except Exception as e:
        print(f"转换失败: {e}")
        return b''


