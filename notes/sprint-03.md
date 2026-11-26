# Sprint 03 — Yapı-farkında chunker

Branch: `sprint/s03-chunker` · Başlangıç: 2026-11-26

## Durum
Sağlık kontrolü düzeltmeleri bitti, planlama ölçümleri yapıldı. **Chunker planı ve tasarım kararları onay bekliyor;**
henüz chunker kodu yok.

## S03 öncesi sağlık kontrolü

Kontrol hiçbir dosya değiştirilmeden yapıldı; bulgular P1–P13 olarak numaralandı. Sahibin kararlarıyla
her düzeltme grubu ayrı commit olarak uygulandı.

| Bulgu | Ne yapıldı | Commit |
|---|---|---|
| (ek) | Dependabot'un `actions/checkout` v6 → v7 PR'ı (#5) sahibi tarafından merge edildi | `0baf20a`, merge `95fe3a5` |
| P1–P3 | `CLAUDE.md`: sprint S03; "learning project" bölümü kaldırıldı; Working mode yenilendi; repo dışı dosya kuralına istisnalar | `8f0f6ec chore: update claude instructions for sprint 03` |
| P5 | `pydantic` doğrudan bağımlılık olarak eklendi (`>=2.14.1`; kurulu sürüm zaten buydu) | `9cb6afb chore(deps): declare pydantic dependency` |
| P6 | `pyproject.toml` açıklaması yazıldı | `081e23d chore: describe the project in pyproject` |
| P7 | `tests/test_target_repo.py`: klonun `HEAD`'i ve tag'i config'deki SHA ile aynı; klon yoksa `skip` | `76e8903 test(config): verify fastapi clone matches pinned version` |
| P8 | Kullanılmayan `noqa` kaldırıldı; ters yazılmış karşılaştırma `expected` değişkeniyle düzeltildi | `3e2cb14 test: fix unused noqa and yoda condition` |
| P9 | `.env.example`, `.gitignore`, `.gitmessage`, `__main__.py` diskte LF'ye çevrildi (silip `git checkout --`; içerik aynı) | commit yok: indeks zaten LF idi, diff oluşmadı |
| P10 | Ruff: `extend-exclude = ["data/**"]`, `force-exclude = true`; `.gitignore`: `.env.*` (`.env.example` hariç). **Kısmi çözüm, aşağıya bak** | `189ff03 chore: exclude data from ruff and ignore env variants` |
| P13 | CI: `push` yalnızca `main`; `timeout-minutes: 10`; `concurrency` (yalnızca PR çalışmaları iptal edilir, `main` çalışmaları tamamlanır); yanlış yorum düzeltildi. Yerelde çalıştırılamaz, doğrulaması PR'ın CI'ında | `200764a ci: limit push trigger and add timeout and concurrency` |
| LICENSE | MIT, "Copyright (c) 2026 Erdem Koray" | `e685a04 docs: add mit license` |
| P11 | README: durum ve roadmap, çalışan komutlar (`scan`, `parse-debug`), proje yapısı, düzeltilmiş clone/checkout komutları, Uygulama Denetimi notu, lisans. Komutlar standart biçimde (`uv run rag`, `uv run pytest`); bu biçimler bu makinede engelli olduğu için burada çalıştırılarak denenmedi | `a31987d docs: update readme` |
| P12 | Sprint notları: eski/çelişen cümleler düzeltildi, `sprint-00`'a "Açık işler", `sprint-02`'ye "Durum" ve "Hakimiyet soruları" açıldı. Mevcut hakimiyet sorularına dokunulmadı, hiçbirine cevap yazılmadı | `23e1995 docs: tidy sprint notes` |

## Planlama ölçümleri (P4 ve boyutlar)

`data/repos/fastapi` 0.143.0, 2026-11-26. Betik `data/out/s03_measure.py` (gitignore'da, repoya girmedi); klon yalnızca okundu.
Gruplar: **kaynak** = scan'in dahil edip test saymadığı 52 dosya; **test** = dahil edilen 616 test dosyası;
**indekslenmeyen** = `docs_src/` ve `scripts/` (499 dosya).

### P4: modül düzeyindeki bileşik ifadeler içindeki tanımlar

| Grup | Bileşik ifade | Tanım içeren | İçlerindeki tanım | Modül düzeyindeki tüm tanımlar |
|---|---|---|---|---|
| kaynak | 6 `try`, 2 `if` | 3 `try` | **3 sınıf** | 290 |
| test | 10 `if`, 3 `with` | 1 `if` | **1 sınıf** | 3743 |
| indekslenmeyen | 11 `if`, 12 `try`, 2 `for` | 0 | 0 | 1024 |

- Kaynaktaki üç tanım da `except ImportError` **yedek dalında**: `Color` ve `PyExtraColor` (`fastapi/encoders.py`),
  `EmailStr` (`fastapi/openapi/models.py`).
- Testteki tek tanım `if TYPE_CHECKING:` altında (`DummyUser`).
- Sınıf gövdelerinde bileşik ifadeye sarılı tanım **yok**.

### Tanım boyutları (bayt, decorator'lar dahil)

| Grup / tür | Adet | p50 | p90 | p99 | En büyük | >4 000 | >8 000 | >32 000 |
|---|---|---|---|---|---|---|---|---|
| kaynak fonksiyon | 169 | 506 | 3 618 | 11 912 | 19 264 | 16 | 10 | 0 |
| kaynak metot | 215 | 498 | 4 080 | 15 105 | 36 943 | 22 | 19 | 1 |
| kaynak sınıf (tamamı) | 121 | 465 | 4 111 | 165 289 | 184 159 | 13 | 4 | 2 |
| kaynak iç fonksiyon | 38 | 421 | 1 562 | 17 728 | 17 728 | 1 | 1 | 0 |
| test fonksiyonu | 3478 | 295 | 1 042 | 7 210 | 383 734 | 145 | 29 | 3 |

- Test grubunda sınıflar (265), metotlar (125) ve iç sınıflar (85) küçük: en büyüğü 1 472 bayt.
- **Dev sınıflar:** `FastAPI` 184 159 bayt / 4 791 satır / 23 metot; `APIRouter` 165 289 bayt / 4 226 satır / 32 metot.
- **Büyüklük imzada:** `FastAPI.__init__` 36 943 baytın 30 178'i imza (989 satır); `APIRouter.head` vb. ~15 000 baytın ~13 400'ü
  imza. Nedeni parametrelerin `Annotated[..., Doc("""...""")]` açıklamaları. 8 000 baytı aşan kaynak fonksiyon/metotlarda
  imzanın payı **%79**, docstring'in payı %2. Yani bu dosyalarda dokümantasyon docstring'de değil, imzada.
- **Dev test fonksiyonu:** `test_include_router_defaults_overrides.py::test_openapi` 383 734 bayt / 6 866 satır (beklenen JSON sözlüğü).

### Ad çakışması ve modül düzeyi kod

- Aynı dosyada yinelenen nitelikli ad: kaynakta **0**; testte 3, hepsi iç fonksiyon.
- Üst düzey tanımların dışında kalan bayt (import, sabit, yorum, boş satır): kaynakta %5, testte %5.
- Tanım içermeyen, boş olmayan dosya: kaynakta **19**, testte 6. Boş dosya: kaynakta 2, testte 92.

## Kararlar ve gerekçeleri
- **Kodu Claude yazar** (çekirdek mantık dahil). Sprint başında plan ve tasarım kararları sunulur, onaydan sonra her adımda
  `pytest`, `ruff check`, `ruff format --check` geçerse commit edilip devam edilir; kapsanmayan bir tasarım kararında durulur.
  Gerekçe: eski "learning project" kuralları çalışma moduyla çelişiyordu ve chunker çekirdek mantık.
- **Repo dışı dosya kuralı:** araç önbellekleri (uv, ruff, pytest) ve pytest geçici klasörleri istisna; geçici betikler ve
  çıktıları `data/out/` altında (gitignore'da). Gerekçe: önceki kural pratikte uygulanamıyordu.
- **Pin testi (P7):** `git -C`, kendi `.git`'i olmayan bir dizinde sessizce üstteki (bu) repoyu cevapladığı için test
  "klon yok" ölçütü olarak `.git` varlığına bakar. Git komutları `--no-optional-locks` ile çalışır, hedef repoya hiçbir şey yazmaz.
  Test geçiyor, klon gizliyken atlanıyor ve yanlış SHA verildiğinde başarısız oluyor (üçü de elle doğrulandı).
- **Ruff dışlamasının sınırı (P10):** `data/repos/fastapi` kendi `pyproject.toml`'una sahip ve ruff her dosyaya en yakın
  yapılandırmayı uygular (`--show-settings` ile doğrulandı: `Settings path: data/repos/fastapi/pyproject.toml`,
  `force_exclude = false`). Bu yüzden kök ayarlar klonun içine **ulaşmaz**: `ruff format data/repos/fastapi/...` klonu
  hâlâ değiştirebilir. Ayarlar `data/` altındaki diğer dosyalar (ör. `data/out/`) için çalışıyor (geçici dosyayla doğrulandı).
  Proje genelinde `ruff ... .` zaten `.gitignore` sayesinde `data/`'ya girmiyor. Kalan boşluk için karar sahibinde (Açık işler 1).

## Doğrulama
- `uv run python -m pytest`: **152 geçti** (düzeltmelerden sonra); `ruff check` ve `ruff format --check` temiz.

## Açık işler
1. P10'un kalan boşluğu: klona açık yolla ruff çalıştırmayı engellemek (seçenekler sahibine sunuldu).
2. S02 PR'ının (#4) CI sonucu teyit edilecek (ayrıntı `sprint-02.md` Açık işler 4).
3. Chunker planının ve tasarım kararlarının onayı.
