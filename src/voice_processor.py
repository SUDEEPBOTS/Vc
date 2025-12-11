import os
import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range, high_pass_filter
import tempfile
from scipy import signal
import aiofiles
import asyncio
import logging
from config import Config

logger = logging.getLogger(__name__)

class VoiceProcessor:
    """
    Professional voice processor for Instagram/TikTok style effects
    """
    
    @staticmethod
    async def download_voice(bot, file_id: str, user_id: int) -> str:
        """Download voice message from Telegram"""
        try:
            file = await bot.get_file(file_id)
            
            # Create temp file path
            filename = f"voice_{user_id}_{int(asyncio.get_event_loop().time())}.ogg"
            file_path = os.path.join(Config.TEMP_DIR, filename)
            
            # Download file
            await file.download(destination_file=file_path)
            
            logger.info(f"✅ Voice downloaded: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"❌ Error downloading voice: {e}")
            return None
    
    @staticmethod
    async def process_voice(input_path: str, filter_type: str = "deep") -> str:
        """
        Apply voice effects based on filter type
        Returns path to processed audio
        """
        try:
            logger.info(f"Processing voice with filter: {filter_type}")
            
            # Convert to WAV if needed
            if not input_path.endswith('.wav'):
                audio = AudioSegment.from_file(input_path)
                wav_path = input_path.rsplit('.', 1)[0] + '.wav'
                audio.export(wav_path, format='wav')
                temp_input = wav_path
            else:
                temp_input = input_path
            
            # Apply selected filter
            if filter_type == "deep":
                output_path = VoiceProcessor._apply_deep_filter(temp_input)
            elif filter_type == "robot":
                output_path = VoiceProcessor._apply_robot_filter(temp_input)
            elif filter_type == "radio":
                output_path = VoiceProcessor._apply_radio_filter(temp_input)
            elif filter_type == "echo":
                output_path = VoiceProcessor._apply_echo_filter(temp_input)
            elif filter_type == "bass":
                output_path = VoiceProcessor._apply_bass_filter(temp_input)
            else:  # clear or unknown
                output_path = temp_input
            
            # Convert to OGG for Telegram
            if output_path.endswith('.wav'):
                audio = AudioSegment.from_wav(output_path)
                ogg_path = output_path.rsplit('.', 1)[0] + '_processed.ogg'
                audio.export(ogg_path, format='ogg', parameters=["-ac", "1"])
                
                # Cleanup
                if temp_input != input_path:
                    os.remove(temp_input)
                os.remove(output_path)
                
                return ogg_path
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error processing voice: {e}")
            return input_path
    
    @staticmethod
    def _apply_deep_filter(input_path: str) -> str:
        """Apply Instagram style deep voice filter"""
        try:
            # Load audio
            y, sr = librosa.load(input_path, sr=44100)
            
            # 1. Pitch shift for deep voice
            y = librosa.effects.pitch_shift(
                y, sr=sr, 
                n_steps=Config.PITCH_SHIFT,
                bins_per_octave=36
            )
            
            # 2. Time stretching (slightly slower)
            y = librosa.effects.time_stretch(y, rate=Config.SPEED_FACTOR)
            
            # 3. Bass enhancement
            sos = signal.butter(4, 150, 'lowpass', fs=sr, output='sos')
            y_bass = signal.sosfilt(sos, y)
            y = y + (y_bass * (Config.BASS_BOOST / 20))
            
            # 4. Reverb effect
            reverb = np.zeros_like(y)
            delay = int(0.1 * sr)
            decay = 0.5
            
            for i in range(delay, len(y)):
                reverb[i] = y[i - delay] * decay
            
            y = y + (reverb * 0.3)
            
            # 5. Normalize
            y = librosa.util.normalize(y)
            
            # Save processed audio
            output_path = input_path.replace('.wav', '_deep.wav')
            sf.write(output_path, y, sr)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in deep filter: {e}")
            return input_path
    
    @staticmethod
    def _apply_robot_filter(input_path: str) -> str:
        """Apply robotic voice effect"""
        try:
            y, sr = librosa.load(input_path, sr=44100)
            
            # Add ring modulation
            t = np.arange(len(y)) / sr
            modulator = np.sin(2 * np.pi * 80 * t)
            y = y * (1 + 0.5 * modulator)
            
            # Pitch shift
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=-2)
            
            # Bandpass filter
            sos = signal.butter(4, [500, 2000], 'bandpass', fs=sr, output='sos')
            y = signal.sosfilt(sos, y)
            
            # Save
            output_path = input_path.replace('.wav', '_robot.wav')
            sf.write(output_path, y, sr)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in robot filter: {e}")
            return input_path
    
    @staticmethod
    def _apply_radio_filter(input_path: str) -> str:
        """Apply AM radio effect"""
        try:
            y, sr = librosa.load(input_path, sr=44100)
            
            # Bandpass filter (AM radio frequency range)
            sos = signal.butter(4, [300, 3000], 'bandpass', fs=sr, output='sos')
            y = signal.sosfilt(sos, y)
            
            # Add noise
            noise = np.random.normal(0, 0.01, len(y))
            y = y * 0.9 + noise * 0.1
            
            # Compress
            y = np.tanh(y * 2) * 0.8
            
            output_path = input_path.replace('.wav', '_radio.wav')
            sf.write(output_path, y, sr)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in radio filter: {e}")
            return input_path
    
    @staticmethod
    def _apply_echo_filter(input_path: str) -> str:
        """Apply echo/delay effect"""
        try:
            y, sr = librosa.load(input_path, sr=44100)
            
            # Create echo
            delay_samples = int(0.3 * sr)
            echo = np.zeros_like(y)
            echo[delay_samples:] = y[:-delay_samples] * 0.6
            
            # Second echo
            delay2 = int(0.6 * sr)
            echo2 = np.zeros_like(y)
            echo2[delay2:] = y[:-delay2] * 0.3
            
            y = y + echo + echo2
            
            output_path = input_path.replace('.wav', '_echo.wav')
            sf.write(output_path, y, sr)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in echo filter: {e}")
            return input_path
    
    @staticmethod
    def _apply_bass_filter(input_path: str) -> str:
        """Apply bass boost effect"""
        try:
            y, sr = librosa.load(input_path, sr=44100)
            
            # Low shelf filter for bass boost
            sos = signal.butter(4, 100, 'lowpass', fs=sr, output='sos')
            y_bass = signal.sosfilt(sos, y)
            
            # Boost bass
            y = y + (y_bass * 1.5)
            
            # High pass to remove rumble
            sos_hp = signal.butter(2, 80, 'highpass', fs=sr, output='sos')
            y = signal.sosfilt(sos_hp, y)
            
            output_path = input_path.replace('.wav', '_bass.wav')
            sf.write(output_path, y, sr)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in bass filter: {e}")
            return input_path
    
    @staticmethod
    async def cleanup_file(file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

# Global voice processor instance
voice_processor = VoiceProcessor()
