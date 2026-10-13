# Sprint 00 — Ortam ve iskelet

## Amaç
Üzerine kod yazılacak çalışan bir proje iskeleti kurmak.

## Yapılanlar
- Proje uv ile `src/coderag` düzeninde kuruldu.
- ruff (lint, format) ve pytest ayarlandı.
- `config.py`: API anahtarları ve hedef repo bilgileri `.env` dosyasından okunuyor.
- `cli.py`: `rag` komutu ve `index`, `search`, `ask` alt komutları eklendi; şimdilik hepsi "Not implemented yet." yazıp çıkıyor.
- FastAPI reposu `data/repos/fastapi` altına klonlandı ve bir sürüme sabitlendi.
- 5 test yazıldı ve geçiyor.

## Kararlar
- API anahtarları zorunlu değil; sadece gerektiği yerde `require` ile kontrol ediliyor.
- `.env` içinde boş bırakılan anahtarlar "yok" sayılıyor.
- FastAPI tag: ... / SHA: ...

## Doğrulama
(`uv run rag --help` ve `uv run pytest -v` çıktılarını buraya yapıştır)

## Hakimiyet soruları
- uv.lock neyi garanti eder?
- src/ düzeni hangi hatayı önler?