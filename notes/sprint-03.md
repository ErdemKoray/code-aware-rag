# Sprint 03 — Yapı-farkında chunker

Branch: `sprint/s03-chunker` · Başlangıç: 2026-11-26

## Durum
Sağlık kontrolü düzeltmeleri bitti, planlama ölçümleri yapıldı, **plan ve tasarım kararları onaylandı (2026-11-26).**
Uygulama adım adım sürüyor (bkz. Adımlar).

## Kapsam
Bu sprint, **orijinal sprint planındaki S03–S05'in** şu parçalarını karşılar: chunk birimleri, sınıfların ele alınışı ve
boyut kuralları.

| Bu sprint (S03) | Sonraki sprintler |
|---|---|
| Chunk birimleri (modül, fonksiyon, sınıf, metot) | **S04:** imza, docstring, decorator listesi, kullanılan import'lar, çağrılar (`calls`), FastAPI route / `Depends` zenginleştirmesi |
| Sınıfların bölünmesi | **S05 (M1):** `ast` ile karşılaştırma, `reports/phase1.md`, golden set v0 |
| Boyut sınırı ve büyük parçaların bölünmesi, `rag chunk-debug`, klon genelinde doğrulama | |

Sonraki alanlar mevcut kurucuları bozmadan eklenebilsin diye `Chunk` anahtar sözcüklü (`kw_only`) bir dataclass olacak;
yeni alanlar varsayılan değerle eklenir. Şimdiden boş yer tutucu alan **açılmaz**.

## Adımlar
| # | Adım | Commit |
|---|---|---|
| 1 | `Settings.max_chunk_bytes`, `Chunk` veri modeli | `5fb4190 feat(config): add max_chunk_bytes setting`, `feat(chunking): add chunk data model` |
| 2 | Fonksiyon chunk'ları (`chunking/chunker.py::chunk_source`) | `feat(chunking): chunk module-level functions` |
| 3 | Sınıfların bölünmesi (`class_header`, `method`, `class`) | karar bekliyor (Açık işler) |
| 4 | Modül düzeyi bloklar, sınıf blokları, yorumların bağlanması, bileşik ifadeler | bekliyor |
| 5 | Sınırı aşan parçaların bölünmesi | bekliyor |
| 6 | `rag chunk-debug` | bekliyor |
| 7 | Klon genelinde kalıcı test, istatistikler (200 bayt altı chunk sayısı dahil), README | bekliyor |

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
| LICENSE | MIT, "Copyright (c) 2026 Koray Erdem" (ilk commit'te ad sırası ters yazılmıştı, düzeltildi) | `e685a04 docs: add mit license`, `dbb0b61 docs: fix license holder name` |
| P11 | README: durum ve roadmap, çalışan komutlar (`scan`, `parse-debug`), proje yapısı, düzeltilmiş clone/checkout komutları, Uygulama Denetimi notu, lisans. Komutlar standart biçimde (`uv run rag`, `uv run pytest`); bu biçimler bu makinede engelli olduğu için burada çalıştırılarak denenmedi | `a31987d docs: update readme` |
| P12 | Sprint notları: eski/çelişen cümleler düzeltildi, `sprint-00`'a "Açık işler", `sprint-02`'ye "Durum" ve "Hakimiyet soruları" açıldı. Mevcut hakimiyet sorularına dokunulmadı, hiçbirine cevap yazılmadı | `23e1995 docs: tidy sprint notes` |
| (ek) | S02 PR CI sonucu (yeşil, Node.js 20 uyarısı yok) kaydedildi | `5ee22e3 docs: close sprint 02 ci item` |
| P10 (ek) | Pin testine klon çalışma ağacının temiz olduğu kontrolü | `95e8103 test(config): require a clean fastapi working tree` |

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

### Karar sonrası ek ölçümler
Betik `data/out/s03_questions.py`; dahil edilen 668 dosya.
- Klonda satır sonları LF (`core.autocrlf=false`), CRLF içeren dosya **0**. 4 000 bayttan uzun tek satır **0**: satır sınırında
  bölme her zaman yeterli.
- Sınıf: kaynakta 121 (63'ü metotsuz), testte 265 (216'sı metotsuz). **Sınıf içinde sınıf yok** (ölçülen "iç sınıflar" fonksiyon
  içindeki sınıflar). Metotsuz olup 4 000 baytı aşan: kaynakta 1.
- Sınıf başına metot imzası listesinin boyutu (bayt):

  | Biçim | p50 | p90 | En büyük | 4 000'i aşan sınıf |
  |---|---|---|---|---|
  | Tam imza | 120 | 1 737 | **149 684** (`FastAPI`; `APIRouter` 128 148) | 2 |
  | Yalnız parametre adları | 49 | 385 | 5 598 (`APIRouter`) | 2 |
  | Yalnız `def ad` | 19 | 95 | 542 (`APIRouter`) | 0 |

## Chunker tasarım kararları (sahip onaylı)

| # | Karar | Gerekçe |
|---|---|---|
| C1 | **Metodu olan sınıf her zaman bölünür** (boyuta bakılmaz): `class_header` chunk'ının metni sınıf başlangıcından (decorator dahil) ilk metoda kadarki satırlar; metot imzalarının listesi `context`'e girer; her metot ayrı chunk. Metodu olmayan sınıf tek `class` chunk'ı. İç fonksiyonlar ebeveyninde kalır; iç sınıflara aynı kural uygulanır | Tutarlı, sembol düzeyinde birimler (sahip, öneri olan "sığıyorsa tek chunk" yerine bunu seçti) |
| C2 | Bitişik tanım dışı ifadeler `module` chunk'ı; bölünen sınıfta metotlar arasındaki satırlar `class_block` | 19 kaynak dosyasında hiç tanım yok; kaybolmamalı |
| C3 | Tanım içeren `if`/`try` bileşik ifadesi bölünmez, modül kodu sayılır; içindeki tanım adları `defined_names`'e yazılır | Yalnızca 4 tanım var ve yedek sınıflar `try` bağlamından kopmamalı |
| C4 | `Settings.max_chunk_bytes = 4000`, ayarlanabilir | Sahip kararı (öneri 8 000 idi). Kaynakta bu sınırı 38 fonksiyon/metot aşıyor |
| C5 | Sınırı aşan parça: önce imza parametre sınırlarından, sonra gövde ifade sınırlarından, son çare satır; her parça `part/part_count` ve başlık bağlamı taşır | Büyüklük çoğunlukla imzada |
| C6 | Dev test fonksiyonları da tamamen bölünür | Tutarlılık; ağırlık retrieval'da düşürülür |
| C7 | `text`, başlangıç–bitiş satırlarının aynen kendisi; yol, nitelikli ad, sınıf imzası `context`'te; boyut sınırı yalnızca `text`'e | Atıfların doğruluğu |
| C8 | Boş olmayan her satır tam olarak bir chunk'ta; tanımın hemen üstündeki yorum tanıma bağlanır | Kayıp ve örtüşme olmamalı |
| C9 | Kimlik `(path, qualname, kind, text)` özeti, birebir aynılara sıra eki; satır numarası kimlikte yok | Kod kayınca kimlik değişmesin (artımlı indeksleme) |
| C10 | `has_error` olan dosya yine chunk'lanır ve işaretlenir, istisna yok | |
| C11 | Sabit boyutlu karşılaştırma chunker'ı S03 dışında (eval sprint'i) | |

Ertelenen: **çok küçük chunk'ları birleştirme yapılmıyor.** S03 sonunda 200 baytın altındaki chunk sayısı türe göre ölçülüp
buraya yazılacak; karar sonra.

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
  Proje genelinde `ruff ... .` zaten `.gitignore` sayesinde `data/`'ya girmiyor.
  **Kalan boşluk için alınan karar:** (a) pin testine klonun çalışma ağacının temiz olduğu kontrolü eklendi
  (`test_clone_working_tree_is_clean`; değiştirilmiş, stage'lenmiş ve takipsiz dosyaları yakalar, `.gitignore`'a takılanları
  göstermez; yardımcı fonksiyon geçici bir git reposunda sınanır); (b) `.claude/settings.json`'daki ruff iznini daraltmayı
  sahibi yapacak. (a) engelleyici değil, **yakalayıcı** bir kontroldür.

### Veri modeli (adım 1)
- `Chunk` (`frozen`, `slots`, `kw_only`): onaylanan alanlar + C10 için `has_error` (dosya düzeyinde işaret). Türetilen
  `size_bytes` (UTF-8).
- `__post_init__` atıf güvencelerini zorlar: satır aralığı geçerli; `text`'teki satır sayısı aralıkla birebir aynı; parça
  numarası geçerli; yalnızca `module` chunk'ının `qualname`'i yok.
- `make_chunk_id`: `sha256(path \0 qualname \0 kind \0 text)`'in ilk 16 hex karakteri (64 bit); birebir aynı chunk'larda
  kaynak sırasına göre `-2`, `-3` eki (C9).

### Fonksiyon chunk'ları (adım 2)
- `chunk_source(source, path)` şimdilik yalnızca modül düzeyindeki fonksiyonları verir; sınıflar, modül kodu, yorum
  bağlama ve boyut bölme sonraki adımlarda.
- Aralık dış node'dan alınır, böylece decorator'lar chunk'a dahildir. İç fonksiyonlar ebeveyninde kalır.
- `context` biçimi: satır başına bir öğe; fonksiyon için `path` ve ad.
- Metin kaynak baytlarının satır dilimidir; CRLF dosyalarda `\r` korunur (C7). Geçersiz UTF-8 baytları `U+FFFD` olur.
- Adı çıkarılamayan (hata kurtarma sonucu) tanımlar fonksiyon chunk'ı olmaz; 4. adımda modül koduna düşecek.

## Doğrulama
- `uv run python -m pytest`: **152 geçti** (sağlık kontrolü düzeltmelerinden sonra); `ruff check` ve `ruff format --check` temiz.
- Adım 2, klon üzerinde (betik `data/out/s03_step2_check.py`): istisna yok; **3 647 fonksiyon chunk'ı** (kaynak 169,
  test 3 478; planlama ölçümüyle birebir); `text`'i atıf yaptığı satırlardan farklı olan 0; repo genelinde yinelenen kimlik
  0; 4 000 baytı aşan 161 (5. adımda bölünecek).
- Adım 2 sonrası `uv run python -m pytest`: **210 geçti**.

## Açık işler
1. P10: `.claude/settings.json`'daki `ruff*` izninin daraltılması (sahibi yapacak; kurallar sohbette verildi). Yakalayıcı test eklendi.
2. ~~S02 PR'ının (#4) CI sonucu~~ **Kapandı:** yeşil, Node.js 20 uyarısı yok (`sprint-02.md` Açık işler 4).
3. **Karar gerekli (adım 3):** `class_header` bağlamındaki metot imzası listesinin biçimi (tam imza 150 KB'a çıkıyor).
4. S03 sonunda 200 bayt altı chunk sayısını türe göre ölç; birleştirme kararı sonra.
