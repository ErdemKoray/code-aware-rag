# Sprint 02 — tree-sitter ayrıştırıcı (`src/coderag/parsing/python.py`)

Branch: `sprint/s02-parser` · Başlangıç: 2026-11-26

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
| 2 | `parsing/python.py`: `parse()`, `ParseResult`, `line_range()` + 31 test | `feat(parsing): add python parser` (hash sonraki commit'te) |

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
- Workflow yerelde çalıştırılamaz; bu değişikliğin doğrulaması bu branch'in push'unda CI'ın yeşil olmasına bağlı.

## Doğrulama
- **Bağımlılıklar (adım 1):** `uv add` sonrası import hemen denendi: `Language(tree_sitter_python.language())`, `Parser(...)`, `parse(b"def f():\n    pass\n")` → kök `module`, `has_error=False`. **Uygulama Denetimi yerel uzantıyı engellemedi.**
- **CI için paket durumu:** `uv.lock`'ta `tree-sitter` 0.27.0 için `cp312` ve `cp314` (manylinux x86_64 dahil) hazır paketleri var; `tree-sitter-python` 0.25.0 `cp310-abi3` (tüm 3.10+ sürümlerinde çalışır). CI'ın kaynaktan derleme yapması gerekmiyor. Gerçek CI sonucu push'a bağlı, henüz görülmedi.
- **Ayrıştırıcı (adım 2), gözlemlenen davranış** (varsayım değil, `parse()` çıktısından; ayrıntılar `notes/tree-sitter.md`'de toplanacak):
  - `async def` ayrı bir node tipi **değil**: `function_definition`, ilk çocuğu anonim `async` jetonu.
  - `decorator` bir **alan adı değil**, `decorated_definition`'ın (tekrarlanan) çocuk node tipi; alan olan `definition`. Testle sabitlendi (`child_by_field_name("decorator") is None`).
  - Hatalı kaynak çökmeden ayrıştırılıyor: `def f(:` için ağaç yine kuruluyor (sıfır genişlikli `MISSING` `)`), sonraki `class_definition` korunuyor; `x = (1, 2` için üst düzeyde `ERROR` node'u var. `has_error` ikisinde de `True`.
  - `class A:\n` ve `def f():\n` (gövdesiz) `has_error=False` veriyor: gramer bunları hata saymıyor. Chunker bunu bilmeli.
- **`line_range` sınır durumu gerçek veride var:** kök `module` her zaman son satırdan sonra 0. sütunda biter; ayrıca FastAPI'de (1167 dosya) kök dışı **29 node** bir sonraki satırın 0. sütununda bitiyor ve hepsi `string_content` (kapanış `"""` satır başındaki docstring'lerin içeriği). `line_continuation` (`\` ile satır devamı) de aynı biçimde biter. Kural uygulanınca `string_content` 1-2, ait olduğu `string` 1-3 satırı verir.
- `uv run python -m pytest`: **139 geçti** (108 eski + 31 yeni).

## Açık işler
- Adımlar tablosundaki parser, `parse-debug`, toplu doğrulama ve `notes/tree-sitter.md` işleri.
