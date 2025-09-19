# storage.py - dosya kayıt/yol yönetimi

from pathlib import Path
from typing import Optional
import os
import shutil
from datetime import datetime

class StorageManager:
    """Dosya depolama yönetimi için yardımcı sınıf"""

    def __init__(self, base_data_dir: Optional[Path] = None):
        if base_data_dir is None:
            # Backend klasöründen data klasörüne git
            backend_dir = Path(__file__).resolve().parent
            base_data_dir = backend_dir.parent / "data"

        self.base_dir = base_data_dir
        self.uploads_dir = base_data_dir / "uploads"
        self.samples_dir = base_data_dir / "samples"

        # Klasörleri oluştur
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.samples_dir.mkdir(parents=True, exist_ok=True)

    def get_upload_path(self, word_id: str, filename: str) -> Path:
        """Kullanıcı yükleme dosyası için yol oluştur"""
        # Güvenli dosya adı oluştur
        safe_filename = self._sanitize_filename(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{word_id}_{timestamp}_{safe_filename}"
        return self.uploads_dir / new_filename

    def get_sample_path(self, word_id: str, filename: str) -> Path:
        """Örnek ses dosyası için yol oluştur"""
        return self.samples_dir / f"{word_id}_{filename}"

    def save_uploaded_file(self, file_content: bytes, word_id: str, original_filename: str) -> Path:
        """Yüklenen dosyayı kaydet ve yolunu döndür"""
        dest_path = self.get_upload_path(word_id, original_filename)

        with dest_path.open("wb") as f:
            f.write(file_content)

        return dest_path

    def copy_file(self, source_path: Path, dest_path: Path) -> bool:
        """Dosya kopyala"""
        try:
            shutil.copy2(source_path, dest_path)
            return True
        except Exception:
            return False

    def file_exists(self, file_path: Path) -> bool:
        """Dosya var mı kontrol et"""
        return file_path.exists() and file_path.is_file()

    def get_file_size(self, file_path: Path) -> Optional[int]:
        """Dosya boyutunu al"""
        if self.file_exists(file_path):
            return file_path.stat().st_size
        return None

    def list_uploaded_files(self, word_id: Optional[str] = None) -> list[Path]:
        """Yüklenen dosyaları listele"""
        if word_id:
            pattern = f"{word_id}_*"
            return list(self.uploads_dir.glob(pattern))
        else:
            return list(self.uploads_dir.glob("*"))

    def cleanup_old_files(self, days_old: int = 30) -> int:
        """Belirtilen gün sayısından eski dosyaları temizle"""
        import time

        now = time.time()
        cutoff = now - (days_old * 24 * 60 * 60)

        deleted_count = 0
        for file_path in self.uploads_dir.glob("*"):
            if file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception:
                    pass  # Silme hatası olursa devam et

        return deleted_count

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Dosya adını güvenli hale getir"""
        # Özel karakterleri kaldır, sadece alfanumerik, nokta ve tire bırak
        import re
        return re.sub(r'[^\w\.-]', '_', filename)

    def get_storage_info(self) -> dict:
        """Depolama bilgilerini döndür"""
        upload_files = list(self.uploads_dir.glob("*"))
        sample_files = list(self.samples_dir.glob("*"))

        return {
            "uploads_dir": str(self.uploads_dir),
            "samples_dir": str(self.samples_dir),
            "upload_count": len(upload_files),
            "sample_count": len(sample_files),
            "total_upload_size": sum(f.stat().st_size for f in upload_files if f.is_file()),
            "total_sample_size": sum(f.stat().st_size for f in sample_files if f.is_file())
        }

# Global instance
storage_manager = StorageManager()