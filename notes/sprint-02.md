# Sprint 02 — tree-sitter ayrıştırıcı (`src/coderag/parsing/python.py`)

Branch: `sprint/s02-parser` · Başlangıç: 2026-11-26 · Son güncelleme: 2026-11-26

## Durum
**Sprint tamamlandı:** kapsamdaki işlerin hepsi yapıldı, PR #4 ile `main`'e merge edildi (`4b6f577`) ve `sprint-02`
etiketlendi. PR'ın CI sonucunun teyidi açık (Açık işler 4).

## Amaç
Python kaynağını tree-sitter ile sözdizimi ağacına çevirmek; ağaçta hata olup olmadığını bildirmek.
S03'teki yapı-farkında chunker bu ağacın üzerine kurulacak.

## Kapsam
- `tree-sitter` ve `tree-sitter-python` bağımlılıkları.
- `parse(source: bytes)` → ağaç + `has_error` bilgisi.
- `rag parse-debug <dosya>`: üst düzey node'ları tip ve satır aralığıyla basar.
- Tüm FastAPI dosyaları istisnasız ayrıştırılmalı; toplam süre ve `has_error` sayısı bu nota yazılır.
- Sözdizimi hatalı kaynak çökmeden ayrıştırılmalı ve `has_error=True` vermeli.
- Testler: async fonksiyon, decorator'lı tanım, iç içe sınıf, hatalı kaynak.
- `notes/tree-sitter.md`: gerçek gözlemden derlenen node tipleri ve alan adları.

## Adımlar ve commit'ler

| Adım | Ne yapıldı | Commit |
|---|---|---|
| Hazırlık | README'ye CI rozeti | `7ae1371 docs: add ci badge to readme` |
| Hazırlık | Sprint 02 başlangıcı (`CLAUDE.md` sprint satırı, bu not) | `6b7e9c3 chore: start sprint 02` |
| Hazırlık | S01 notunda Python 3.12 maddesi kapatıldı (CI'da 3.12 ve 3.14 yeşil) | `c203d99 docs: close sprint 01 python 3.12 item` |
| Hazırlık | CI aksiyonları Node 24'e yükseltildi, Dependabot eklendi | `7480e2b ci: upgrade actions to node24 and enable dependabot` |
| 1 | `tree-sitter` 0.27.0 ve `tree-sitter-python` 0.25.0 eklendi | `983c782 chore(deps): add tree-sitter and tree-sitter-python` |
| 2 | `parsing/python.py`: `parse()`, `ParseResult`, `line_range()` + 31 test | `663a8be feat(parsing): add python parser` |
| 3 | `rag parse-debug <dosya>` + 9 test | `d4d7378 feat(cli): add parse-debug command` |
| 4 | Tüm FastAPI dosyalarının ayrıştırılması: kalıcı test (klon yoksa `skip`) + sayılar | `1e73578 test(parsing): parse every fastapi file` |
| 5 | `notes/tree-sitter.md`: gözlemden derlenen node tipleri, alanlar, sınır durumları | `4c941d7 docs: add tree-sitter node reference` |
| 5 | Son commit hash'i bu nota işlendi | `d03927d docs: fill in sprint 02 commit hashes` |

## Kararlar ve gerekçeleri

1. **`parse()` bir `ParseResult` döndürür** (`frozen=True, slots=True`; alanlar `tree`, `source`; `has_error` bir property).
   Gerekçe: `has_error` zaten `tree.root_node.has_error`'dan türer, ayrı alan olarak saklamak tutarsızlık riski yaratır. `source` S03'te node metnini çıkarmak için taşınır. Anlam: tree-sitter'da `has_error`, hem `ERROR` hem `MISSING` node'larını sayar.
2. **Satır aralığı yardımcısı 1 tabanlı ve kapsayıcı** (`(başlangıç, bitiş)`). tree-sitter 0 tabanlı satır verir.
   Ek koşul: node bir sonraki satırın 0. sütununda bitiyorsa bitiş satırı bir fazla gösterilmez (bu sınır durumu testlidir). Gerekçe: ileride tüm `dosya:satır` atıfları bu yardımcıya dayanacak.
3. **Hatalı fixture'lar testlerde satır içi `bytes`**, `.py` dosyası değil. Gerekçe: hatalı bir `.py` dosyası `ruff check` ve `ruff format --check`'i, yani CI'ı kırar.
4. **"Tüm FastAPI dosyaları" iki küme:** (a) scan'in 668 dahil dosyası, (b) `git ls-files "*.py"` ile 1167 dosyanın tamamı (`docs_src/`, `scripts/` dahil). Sayılar ayrı raporlanır.
   Doğrulama **kalıcı bir test** olur; klon yoksa kendini `skip` eder (CI'da klon yok). Süre yalnızca bu notta tutulur, testte değil.
5. **`parse-debug` çıktısı:** üst düzey adlandırılmış node'lar (yorumlar dahil, anonim jetonlar hariç); satır aralığı ASCII tireyle (`L12-30`); üstte `has_error` satırı; fonksiyon ve sınıflarda `name=...`; dosya yoksa çıkış kodu 2; `has_error` olan dosyada çıkış kodu 0 (araç hatayı raporlar, hüküm vermez).
6. **Parser yaşam döngüsü:** `Language` modül yüklenirken bir kez, `Parser` her çağrıda yeni oluşturulur (Parser iş parçacığı güvenli değil; HTTP API sprint'inde sorun çıkmasın).
7. **Kodlama sınırı:** girdi `bytes`, tree-sitter UTF-8 varsayar. `coding:` bildirimiyle başka kodlama kullanan dosya çıkarsa burada belirtilir.
8. **Sürümler** `uv add`'in seçtiği güncel sürümler; sabitlemeyi `uv.lock` yapar.

### CI bakımı
- S01'deki CI çalışmasında Node.js 20 uyarısı çıktı. `actions/checkout` `v4` → `v6`, `astral-sh/setup-uv` `v6` → `v7` (Node 24 çalışma zamanı); sürümler sahibinin talimatıyla seçildi, ağdan ben doğrulamadım (`gh` yok).
- `.github/dependabot.yml`: yalnızca `github-actions` ekosistemi, kök dizin, haftalık. Python bağımlılıkları (`uv`) bilerek kapsam dışı; `uv.lock` elle güncelleniyor.
- Workflow yerelde çalıştırılamaz; doğrulaması CI'dadır (Açık işler 4).
- Sprintten sonra Dependabot `actions/checkout` v6 → v7 PR'ını (#5) açtı; sahibi merge etti.

## Doğrulama
- **Bağımlılıklar (adım 1):** `uv add` sonrası import hemen denendi: `Language(tree_sitter_python.language())`, `Parser(...)`, `parse(b"def f():\n    pass\n")` → kök `module`, `has_error=False`. **Uygulama Denetimi yerel uzantıyı engellemedi.**
- **CI için paket durumu:** `uv.lock`'ta `tree-sitter` 0.27.0 için `cp312` ve `cp314` (manylinux x86_64 dahil) hazır paketleri var; `tree-sitter-python` 0.25.0 `cp310-abi3` (tüm 3.10+ sürümlerinde çalışır). CI'ın kaynaktan derleme yapması gerekmiyor. Bu, kilit dosyasından çıkarılan bir beklentidir; CI sonucu için Açık işler 4.
- **Ayrıştırıcı (adım 2), gözlemlenen davranış** (varsayım değil, `parse()` çıktısından; ayrıntılar `notes/tree-sitter.md`'de toplanacak):
  - `async def` ayrı bir node tipi **değil**: `function_definition`, ilk çocuğu anonim `async` jetonu.
  - `decorator` bir **alan adı değil**, `decorated_definition`'ın (tekrarlanan) çocuk node tipi; alan olan `definition`. Testle sabitlendi (`child_by_field_name("decorator") is None`).
  - Hatalı kaynak çökmeden ayrıştırılıyor: `def f(:` için ağaç yine kuruluyor (sıfır genişlikli `MISSING` `)`), sonraki `class_definition` korunuyor; `x = (1, 2` için üst düzeyde `ERROR` node'u var. `has_error` ikisinde de `True`.
  - `class A:\n` ve `def f():\n` (gövdesiz) `has_error=False` veriyor: gramer bunları hata saymıyor. Chunker bunu bilmeli.
- **`line_range` sınır durumu gerçek veride var:** kök `module` her zaman son satırdan sonra 0. sütunda biter; ayrıca FastAPI'de (1167 dosya) kök dışı **29 node** bir sonraki satırın 0. sütununda bitiyor ve hepsi `string_content` (kapanış `"""` satır başındaki docstring'lerin içeriği). `line_continuation` (`\` ile satır devamı) de aynı biçimde biter. Kural uygulanınca `string_content` 1-2, ait olduğu `string` 1-3 satırı verir.
- **`parse-debug` (adım 3):** çıktı biçimi: ilk satır `has_error: True|False`; sonra üst düzey adlandırılmış node başına bir satır: `tip  Lx-y` (+ `  name=...`), tip sütunu en uzun tipe göre hizalı; boş dosyada `(no top-level nodes)`. `decorated_definition` için `name=`, sardığı fonksiyon/sınıfın adını gösterir (sahip talimatı: "fonksiyon ve sınıflarda"). Hatalı dosyada çıkış kodu 0, okunamayan dosya/dizinde `Error: cannot read ...` ve çıkış kodu 2. Çıktı ASCII (`isascii` testli). Gerçek dosyada (`fastapi/params.py`) elle denendi.
- **Toplu doğrulama: tüm FastAPI dosyaları (adım 4)** (`data/repos/fastapi` 0.143.0 sabit sürümü, 2026-11-26; ölçüm betiği scratchpad'de, repoya girmedi). Dosyalar belleğe önceden okundu; süre **yalnızca `parse()`** çağrılarının toplamı, 3 çalıştırma, ortanca verildi:

  | Küme | Dosya | Boyut | `parse()` süresi (3 çalıştırma) | Ortanca | İstisna | `has_error` |
  |---|---|---|---|---|---|---|
  | (a) scan'in dahil dosyaları | 668 | 3 806 063 bayt | 0.452 / 0.434 / 0.444 sn | **0.444 sn** | **0** | **0** |
  | (b) `git ls-files "*.py"` (tamamı, `docs_src/` ve `scripts/` dahil) | 1167 | 4 168 417 bayt | 0.491 / 0.461 / 0.457 sn | **0.461 sn** | **0** | **0** |

  - Hiçbir dosyada `ERROR` ya da `MISSING` node'u yok; yani gramer FastAPI 0.143.0'ın bütün yazımını (3.10+ sözdizimi örnekleri dahil) tanıyor.
  - (b)'de fazladan 499 dosya (`docs_src/`, `scripts/`) yalnızca ~17 ms ekliyor: bunlar küçük dosyalar (≈360 KB toplam). Ayrıştırma hızı kabaca 8-9 MB/sn; indeksleme hattında ayrıştırma darboğaz olmayacak.
  - Kalıcı test `tests/test_parsing_fastapi.py` iki kümeyi de ayrı ayrı sınar ve `has_error == 0` ister. Klon (`Settings().fastapi_repo_path`) yoksa kendini `skip` eder: yerelde klon gizlenerek 2 skip doğrulandı, CI'da klon olmadığı için atlanacak (S01'de konuşulan "klon gerektiren test kendini atlasın" kuralının ilk kullanımı).
  - Sürüm kayması riski: `tree-sitter-python` güncellenirse (yeni gramer) bu test hata sayısını yakalayan ilk alarm olur.
- `uv run python -m pytest`: **150 geçti** yerelde (108 eski + 31 ayrıştırıcı + 9 CLI + 2 toplu FastAPI testi); CI'da klon olmadığı için 148 geçer, 2 atlanır.

- **`notes/tree-sitter.md` (adım 5):** 1167 dosyanın node/alan sayımından ve elle denenen örneklerden derlendi. Gramerle/beklentiyle **farklı çıkan 7 şey** belgenin 2. bölümünde tablo olarak: `async` ayrı tip değil; `decorator` alan değil çocuk tipi; `typed_parameter`'da `name` alanı yok; docstring ayrı node değil; `comment` her yerde çıkabiliyor (ör. satır sonu yorumu `function_definition`'ın çocuğu); gövdesiz `def f():` `has_error=False` veriyor; FastAPI'de hiç `ERROR`/`MISSING` yok.

## Açık işler
1. **S03'e devredilen sorular** (ayrıntı `notes/tree-sitter.md` bölüm 6 ve 11): modül düzeyindeki `if_statement` (23) ve `try_statement` (18) içindeki tanımlar nasıl ele alınacak? Bunların içinde kaç tanım olduğu **ölçülmedi**.
2. `has_error=False` her zaman "geçerli kod" demek değil (gövdesiz `def f():`). Chunker'ın buna güvenmemesi gerek.
3. Python dışı kodlama bildirimi (`# -*- coding: latin-1 -*-`) olan dosya FastAPI'de çıkmadı; sorun gözlenmedi.
4. **CI sonucu teyit bekliyor:** branch push edildi ve PR #4 merge edildi. Sahibin 2026-11-26 tarihli mesajında "CI yeşil geçti" yazıyordu, ancak aynı satırda "Bu satırı Actions sonucuna göre düzelt" notu da duruyordu; bu yüzden doğrulanmış sayılmadı. Teyit edilecekler: 3.12 ve 3.14 matrisinin yeşil olması (`tree-sitter` kurulumu dahil) ve 2 klon testinin CI'da atlanması. Actions sonucu Claude oturumundan görülemiyor.

## Hakimiyet soruları
- `has_error=False` neden "kod geçerli" anlamına gelmez? Bir örnek ver.
- Bir fonksiyonun decorator'lar dahil satır aralığını hangi node'dan alırsın, neden?
- `line_range()` neden `end_point.row + 1` ile yetinmiyor?
- Ağaçta bir fonksiyonun `async` olduğunu nasıl anlarsın?
