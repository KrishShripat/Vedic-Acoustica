import librosa
import numpy as np
import scipy.signal


SR = 22050
HOP_LENGTH = 512
N_MFCC = 13
N_CHROMA = 22


def extract_features(audio_path):
    y, sr = librosa.load(audio_path, sr=SR)
    duration = librosa.get_duration(y=y, sr=sr)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH)

    chroma = librosa.feature.chroma_stft(
        y=y, sr=sr, n_fft=2048, hop_length=HOP_LENGTH, n_chroma=N_CHROMA,
    )

    spectral_centroid = librosa.feature.spectral_centroid(
        y=y, sr=sr, hop_length=HOP_LENGTH,
    )[0]

    spectrogram = np.abs(librosa.stft(y, hop_length=HOP_LENGTH))
    spectrogram_db = librosa.amplitude_to_db(spectrogram, ref=np.max)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if hasattr(tempo, '__len__'):
        tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
    else:
        tempo = float(tempo)

    frequencies, times, stft_mag = scipy.signal.stft(y, fs=sr, nperseg=2048)
    dominant_freqs = []
    for t_idx in range(stft_mag.shape[1]):
        col = np.abs(stft_mag[:, t_idx])
        peak_idx = np.argmax(col)
        dominant_freqs.append(float(frequencies[peak_idx]))

    return {
        'mfcc': mfcc,
        'chroma': chroma,
        'spectral_centroid': spectral_centroid,
        'spectrogram': spectrogram_db,
        'dominant_frequencies': dominant_freqs,
        'tempo': tempo,
        'duration': duration,
        'sr': sr,
        'y': y,
    }
