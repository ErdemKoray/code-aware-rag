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
- FastAPI tag: 0.143.0 / SHA: f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007

## Doğrulama
`uv run rag --help` ve `uv run pytest -v` çıktıları sprint sırasında bu nota kaydedilmedi. Kod o tarihten sonra
değiştiği için burada sonradan üretilmiş bir çıktıya yer verilmiyor; sprint sonundaki durum `sprint-00` etiketindedir.
Güncel not: bu makinede başlatıcı `.exe` dosyaları Windows Uygulama Denetimi tarafından engellendiğinden komutlar
`uv run python -m coderag --help` ve `uv run python -m pytest` biçiminde çalıştırılıyor.

## Açık işler
- Aşağıdaki hakimiyet soruları cevaplanacak (sahibi yazacak).

## Hakimiyet soruları
- uv.lock neyi garanti eder?
- src/ düzeni hangi hatayı önler?