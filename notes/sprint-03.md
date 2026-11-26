# Sprint 03 — Yapı-farkında chunker

Branch: `sprint/s03-chunker` · Başlangıç: 2026-11-26

## Durum
**Kapsamdaki yedi adımın hepsi bitti (2026-11-26).** `chunk_source()` indekslenen her dosyayı chunk'lara ayırıyor; garantiler
klonun tamamında kalıcı testle sınanıyor. Push, PR, CI sonucu, merge ve `sprint-03` etiketi sahibinde. Açık kalanlar en altta.

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
| 1 | `Settings.max_chunk_bytes`, `Chunk` veri modeli | `5fb4190 feat(config): add max_chunk_bytes setting`, `ff755d3 feat(chunking): add chunk data model` |
| 2 | Fonksiyon chunk'ları (`chunking/chunker.py::chunk_source`) | `245fea8 feat(chunking): chunk module-level functions` |
| (ek) | `.claude/settings.json`: geniş `ruff*` izinleri sahibi tarafından kaldırıldı | `7493ab6 chore: narrow ruff permissions to the project root` |
| 3 | Sınıfların bölünmesi (`class_header`, `method`, `class`, iç sınıflar) | `0e4c93a feat(chunking): split classes into header and members` |
| 4 | Modül düzeyi bloklar, sınıf blokları, yorumların bağlanması, bileşik ifadeler | `cdf82e1 feat(chunking): add module and class blocks` |
| 5 | Sınırı aşan parçaların bölünmesi (`chunking/split.py`) | `c5b457a feat(chunking): split oversized chunks` |
| 6 | `rag chunk-debug` | `dd347f5 feat(cli): add chunk-debug command` |
| 7a | Klon genelinde kalıcı test (`tests/test_chunking_fastapi.py`) | `9a9439d test(chunking): check chunk guarantees on fastapi` |
| 7b | İstatistikler (200 bayt altı dahil), README | `docs: record sprint 03 results` |

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
| S1 | `class_header` bağlamındaki metot listesi yalnızca `def ad` / `async def ad` | Tam imzalar `FastAPI` için 150 KB; parametreler zaten metot chunk'larında |
| S2 | İç sınıf da başlığı bitirir ve kendi chunk'larını alır; metodu olmayıp iç sınıfı olan sınıf da bölünür | C1'deki "ilk metoda kadar" ile "iç sınıflara aynı kural" çakışmasını çözer |

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

### Sınıfların bölünmesi (adım 3)
- "Üye" = sınıf gövdesinin doğrudan çocuğu olan metot ya da iç sınıf. Bileşik ifade içindeki tanımlar üye değildir (C3).
- Başlık: sınıfın dış node'unun ilk satırından ilk üyeden önceki son dolu satıra kadar.
- İlk üye başlığın `:` satırında başlıyorsa (`class A: def f(self): ...`) sınıf bölünmez: bir satır tek bir chunk'a ait olabilir.
- Metot bağlamı: `path`, `Sınıf.metot`, doğrudan sınıfın `class ...:` imzası (decorator'sız, çok satırlıysa olduğu gibi).
  Başlık bağlamı: `path`, ad, metot listesi.

### Satır sahipliği (adım 4)
- Kendi chunk'ı olan tanımlar ("üyeler") satır aralıklarını alır: decorator'lar dış node'dan gelir, hemen üstteki **yalnız
  yorum satırları** (arada boş satır yok, başka bir üyeye ait değil) eklenir. Üyeler arasında kalan dolu satırlar blok olur:
  modülde `module`, sınıfta ilk üyeden öncesi `class_header`, sonrakiler `class_block`. Bloklar baştan ve sondan boş satır
  içermez. Böylece C8 yapı gereği sağlanır.
- "Yorum satırı" tree-sitter'ın `comment` node'undan belirlenir; string içindeki `#` satırı yorum sayılmaz.
- Başka koda ait bir satırda başlayan tanım (yalnız hatalı ya da tek satırlık yazımlarda) kendi chunk'ını almaz.
- `defined_names`: bloğun içinde kalıp kendi chunk'ı olmayan en dış tanımlar (pratikte `if`/`try` içindekiler, C3). Sınıf
  içinde `Sınıf.ad` biçiminde. Bileşik ifade komşu modül koduyla aynı `module` chunk'ına girer ve bölünmez (boyut sınırı hariç).

### Boyut bölme (adım 5)
- `chunk_source(source, path, max_chunk_bytes)`; sınır zorunlu parametre (`Settings` ile tek kaynak), `<= 0` ise `ValueError`.
- `LineSplitter`: aralık sığmıyorsa ağaçta kesilebilecek **en üst düzey** bulunur (modül/blok ifadeleri; decorator ile tanım;
  fonksiyonda parametreler ve gövde; bileşik ifadelerde alt bloklar ve `elif`/`except` vb. dallar). Her dilim aynı yolla
  özyinelemeli bölünür, sonra komşu parçalar sığdıkça **açgözlü** birleştirilir. Alt sınır yoksa (ör. dev sözlük) satır satır.
- Yorum satırları kesim noktası değildir; altlarındaki ifade/parametreyle birlikte gider.
- Sınıra sığmayan tek satır bölünmez (C7: metin satırların aynısı).
- Her parça aynı `kind`, `qualname`, `context`'i taşır; `part/part_count` 1 tabanlı. Parçalar baştan/sondan boş satır içermez.
  `defined_names` adın başladığı parçaya yazılır. Aynı kurallar `module`, `class_header`, `class_block`, `class` için de geçerli.

### `rag chunk-debug <dosya>` (adım 6)
- Çıktı: `has_error` satırı, `chunks: N (max size: B bytes)`, sonra chunk başına bir satır: tür, `Lx-y`, bayt boyutu, nitelikli ad,
  bölünmüşse `[i/n]`, varsa `defines: ...`. Sınır `Settings.max_chunk_bytes`.
- `parse-debug` ile aynı davranış: sözdizimi hatalı dosyada çıkış kodu 0, okunamayan yolda `Error: cannot read ...` ve 2
  (okuma ortak `_read_source` yardımcısında). Gerçek dosyada elle denendi (`fastapi/encoders.py`).
- İlk çalıştırmada bir test başarısızdı: beklenen metot boyutunu yanlış hesaplamıştım (32 değil 29 bayt).

## Sonuçlar (S03 sonu)

`data/repos/fastapi` 0.143.0, `max_chunk_bytes = 4000`, 2026-11-26. Betik `data/out/s03_stats.py` (repoya girmedi).

**668 dosya → 5 737 chunk** (kaynak 680, test 5 057, yani %88 test). Süre 3 çalıştırmada 0,755 / 0,782 / 0,781 sn
(ortanca **0,781 sn**). 184 birim 725 parçaya bölündü (161 fonksiyon, 22 metot, 1 sınıf). `context` ortanca 66, en çok 570 bayt.

| Tür | Kaynak | Test | p50 bayt | p90 bayt | En büyük |
|---|---|---|---|---|---|
| `module` | 73 | 816 | 140 | 349 | 2 945 |
| `function` | 201 | 3 909 | 310 | 2 948 | 4 000 |
| `class` | 62 | 215 | 79 | 212 | 3 978 |
| `class_header` | 57 | 49 | 46 | 929 | 2 971 |
| `method` | 287 | 68 | 622 | 3 728 | 3 999 |
| `class_block` | 0 | 0 | | | |

### 200 baytın altındaki chunk'lar (birleştirme kararı için; birleştirme **yapılmadı**)

Toplam **2 320 / 5 737 (%40)**: kaynak 178, test 2 142. (100 bayt altı 824, kaynak 82; 50 bayt altı 307, kaynak 21.)

| Tür | Türün tamamı | 200 B altı | Kaynak | Test | Bölünmüş birimin parçası | Yalnız yorum |
|---|---|---|---|---|---|---|
| `module` | 889 | 668 | 33 | 635 | 0 | 74 |
| `function` | 4 110 | 1 210 | 26 | 1 184 | 138 | 0 |
| `class` | 277 | 249 | 37 | 212 | 0 | 0 |
| `class_header` | 106 | 76 | 28 | 48 | 0 | 0 |
| `method` | 355 | 117 | 54 | 63 | 2 | 0 |
| `class_block` | 0 | 0 | 0 | 0 | 0 | 0 |

Okuma notları (karar değil, veri):
- Küçüklerin %92'si test dosyalarından.
- 140'ı, açgözlü paketlemeden artan **bölme kuyrukları** (138 fonksiyon, 2 metot parçası): birleştirme düşünülürse en ucuz
  aday, parçaları dengeli bölmek.
- Küçük `module` chunk'larının 74'ü yalnız yorum (bölüm başlıkları); kalanı çoğunlukla import blokları ve kısa ifadeler.
- `class_header`'ların çoğu küçük (p50 46 bayt): C1 gereği metodu olan her sınıf bölündüğünden başlık sıklıkla tek satır.

### Kalıcı klon testi (`tests/test_chunking_fastapi.py`, klon yoksa `skip`)
Her dolu satır tam olarak bir chunk'ta; metin atıf satırlarıyla birebir; sınırı aşan çok satırlı chunk yok; kimlikler repo
genelinde benzersiz; sözdizimi işareti yok; parçalar ardışık ve eksiksiz; iki çalıştırma aynı; modül düzeyindeki her fonksiyonun
ve sınıf metodunun (chunker'dan bağımsız ağaç gezisiyle bulunan) kendi chunk'ı var; sınırın yarısından küçük hiçbir parametre
ortadan kesilmiyor.

## Doğrulama
- `uv run python -m pytest`: **346 geçti** (S03 sonu); klon yokken klona bağlı testler atlanır.
- Adım 5, klon üzerinde (`data/out/s03_step5_check.py`, sınır 4 000): 668 dosya → **5 737 chunk**, 0,80 sn. Kayıp satır 0,
  çift satır 0, atıf farkı 0, yinelenen kimlik 0, **sınırı aşan chunk 0**. Bölünen birim 184 → 725 parça (161 fonksiyon,
  22 metot, 1 sınıf). En çok parça: `test_include_router_defaults_overrides.py::test_openapi` **98**;
  `test_application.py::test_openapi_schema` 16; `FastAPI.__init__` 11 (parçalar parametre sınırlarında başlıyor).
- Adım 5 testlerinde ilk çalıştırmada 3 test başarısız oldu: hata testlerdeki bayt hesabımdaydı (beklenen dilim sınırdan
  uzundu), kodda değil; sınırlar düzeltildi.
- Adım 4, klon üzerinde (`data/out/s03_step4_check.py`): 668 dosya → **5 196 chunk** (`function` 3 647, `module` 889,
  `method` 278, `class` 276, `class_header` 106, **`class_block` 0**: FastAPI'de metotlar arasında sınıf kodu yok).
  Chunk'sız dolu satır **0**, iki chunk'ta geçen satır **0**, atıf farkı 0, yinelenen kimlik 0. `defined_names` taşıyan
  3 chunk: `Color`/`PyExtraColor`, `EmailStr`, `DummyUser`. Yalnız yorumdan oluşan 76 chunk (çoğu bölüm başlığı yorumu).
  4 000 baytı aşan 184 (5. adım).
- `uv run python -m pytest`: **152 geçti** (sağlık kontrolü düzeltmelerinden sonra); `ruff check` ve `ruff format --check` temiz.
- Adım 2, klon üzerinde (betik `data/out/s03_step2_check.py`): istisna yok; **3 647 fonksiyon chunk'ı** (kaynak 169,
  test 3 478; planlama ölçümüyle birebir); `text`'i atıf yaptığı satırlardan farklı olan 0; repo genelinde yinelenen kimlik
  0; 4 000 baytı aşan 161 (5. adımda bölünecek).
- Adım 2 sonrası `uv run python -m pytest`: **210 geçti**.

## Açık işler
1. P10: sahibi geniş `ruff*` izinlerini kaldırdı (`7493ab6`). Önerilen dar kurallar `settings.json`'da **yok**; gitignore'daki
   `settings.local.json`'daki kurallar dışında her ruff çağrısı onay ister. İstenirse dar kurallar sahibi tarafından eklenebilir.
   Yakalayıcı test (temiz çalışma ağacı) yerinde.
2. ~~S02 PR'ının (#4) CI sonucu~~ **Kapandı:** yeşil, Node.js 20 uyarısı yok (`sprint-02.md` Açık işler 4).
3. ~~Metot imzası listesinin biçimi~~ **Karara bağlandı** (S1, S2).
4. ~~200 bayt altı ölçümü~~ **Yapıldı** (Sonuçlar). **Birleştirme kararı sahibinde.**
5. Sonraki sprintlere: S04 zenginleştirme alanları; S05 `ast` karşılaştırması, `reports/phase1.md`, golden set v0 (bkz. Kapsam).
6. Chunk boyutu bayt cinsinden; gerçek token sayısı embedding sprint'inde ölçülecek.
7. `test_openapi` tek başına 98 chunk üretiyor (C6): retrieval/eval'de test ağırlığı düşürülürken izlenmeli.
8. Bu branch henüz push edilmedi: S03'ün ve P13'te değişen `ci.yml`'in CI sonucu görülmedi.

## Hakimiyet soruları
- Her dolu satırın tam olarak bir chunk'ta olması yapının neresinden geliyor?
- Bir metodun üstündeki yorum satırı hangi chunk'a gider; arada boş satır olursa ne değişir?
- 4 000 bayttan büyük bir fonksiyon hangi sırayla bölünür, "son çare" ne zaman devreye girer?
- Chunk kimliğinde neden satır numarası yok, aynı metin iki kez geçerse ne olur?
