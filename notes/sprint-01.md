# Sprint 01 — Dosya tarayıcı (`src/coderag/scan.py`)

Branch: `sprint/s01-scanner` · Başlangıç: 2026-11-18 · Son güncelleme: 2026-11-25

## Amaç
FastAPI reposunda indekslenecek `.py` dosyalarının **deterministik** listesini üretmek.
Dışlanan her dosya için bir **gerekçe kodu** vermek.

## Durum
Veri modeli, `is_test_path`, `load_gitignore` ve `scan()` iskeleti (gezme, budama, sıralama) bitti.
`unreadable_dirs` (listelenemeyen klasörler), `SYMLINK` ve `GITIGNORED` kuralları bitti. Boyut ve okunamaz dosya kuralları ile gerçek repo doğrulaması bekliyor: **c2c–c2d**.

## Adımlar ve commit'ler

| Adım | Ne yapıldı | Commit |
|---|---|---|
| Hazırlık | `pathspec` bağımlılığı eklendi | `dbceccc chore(deps): add pathspec for gitignore matching` |
| Hazırlık | Satır sonları LF'e normalize edildi | `3d2a4d5 chore: normalize line endings to lf` |
| Hazırlık | FastAPI tag/SHA sabitlendi, SHA düzeltildi | `93641cf`, `ab284ee` (`fix(config)`) |
| Config | `Settings.max_file_size_bytes` (varsayılan 500_000, `gt=0`) + 3 test | `8590d0d feat(config): add max_file_size_bytes setting` |
| Çalışma modu | Claude Code gözetimli yazım moduna alındı | `1d383dd` |
| Veri modeli | `ExclusionReason`, `IncludedFile`, `ExcludedFile`, `ScanResult`, `PRUNED_DIR_NAMES`, `test_count`, `exclusion_counts`, `largest` | `e192b5a feat(scan): add scan result data model` |
| a) | `is_test_path` | `08d9409 feat(scan): add is_test_path helper` |
| b) | `load_gitignore` | `3ca6a35 feat(scan): load root gitignore` |
| c1) | `scan()` iskeleti: doğrulama, gezme, budama, `.py` filtresi, sıralama | `f2ff1d1 feat(scan): walk and prune directories` |
| Altyapı | `requires-python` `>=3.12`, `uv.lock` ve README güncellendi | `9a2489c chore: support python 3.12 and later` |
| c2a) | `ScanResult.unreadable_dirs` + `os.walk(onerror=...)` | `feat(scan): report directories that cannot be listed` (hash c2d'de) |
| c2b) | `SYMLINK` ve `GITIGNORED` kontrolleri (`_classify_file`) | `feat(scan): exclude symlinks and gitignored files` (hash c2d'de) |
| c2c) | `TOO_LARGE` ve `UNREADABLE` (dosya) kontrolleri, öncelik testleri | **bekliyor** |
| c2d) | Gerçek FastAPI klonunda doğrulama, sonuçlar notlara | **bekliyor** |

## Kararlar ve gerekçeleri

### Tarayıcı kuralları (K1–K10)

- **K1 — Tek gerekçe, sabit öncelik sırası.** İlk eşleşen kural kazanır.
  Gerekçe: basit ve test edilebilir; her dosyanın neden dışlandığı tek cevapla belli olur.
- **K2 — Kontrol sırası:** klasör budama → symlink → gitignore → boyut → okunamaz.
  Yalnızca `.py` dosyaları aday, diğer uzantılar hiç kayıt üretmez.
  Gerekçe: link hedefini okumadan dışlıyoruz, budanan klasörlere hiç girmiyoruz, `.md` gibi dosyalar listeyi doldurmasın.
- **K3 — Budanan klasörlerin içi raporlanmaz;** budanan klasörler özette (`pruned_dirs`) listelenir.
  Gerekçe: içlerindeki dosyalar zaten `.py` adayı değil ya da ilgisiz.
- **K4 — Testler dışlanmaz,** dahil edilen kayıtta `is_test` bayrağıyla etiketlenir. `TEST_FILE` gerekçe kodu yok.
  Gerekçe: planda testlerin indekse girip aramada düşük ağırlık alması kararlaştırıldı; eval'de "testler dahil/hariç" karşılaştırması yapılabilsin.
- **K5 — Test tespiti:** dizin bileşenlerinden biri `tests` veya `test`; ya da dosya adı `test_*.py`, `*_test.py`, `conftest.py`.
  Gerekçe: FastAPI'deki `tests/` ve `scripts/tests/` yapısını yakalar.
  Sınır: kural yalnızca dizin bileşenlerine uygulanır, dosya adına değil; `test.py` ve `pkg/tests.py` test sayılmaz. Büyük/küçük harfe duyarlı.
- **K6 — Budanan klasörler:** `.git`, `.venv`, `venv`, `__pycache__`, `node_modules`, `build`, `dist`, `.tox`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `docs_src`, `scripts`.
  Gerekçe: `docs_src` yüzlerce küçük eğitim örneği içeriyor ve iç işleyiş sorularında aramayı boğar; `scripts` geliştirme araçları. Liste modül sabiti (`PRUNED_DIR_NAMES`). Eşleşme tam ad üzerinden (`scripts_extra` budanmaz).
- **K7 — Boyut eşiği 500 KB (`500_000` bayt);** `size_bytes <= eşik` dahil, büyükse `TOO_LARGE`. Eşik `Settings.max_file_size_bytes` ile ayarlanabilir.
  Gerekçe: `applications.py`, `routing.py` gibi çekirdek dosyalar uzun docstring'ler yüzünden büyük; düşük eşik onları yanlışlıkla dışlar. **Eşik veriyle doğrulanacak** (aşağıda açık işler).
  `1 KB` yerine bayt kullanıldı çünkü "KB" 1000 mi 1024 mü belirsiz; birim alan adında.
- **K8 — Tüm sembolik linkler `SYMLINK` ile dışlanır, izlenmez.** Klasör linkleri gezilmez ve kayıt üretmez.
  Gerekçe: döngü riski yok; Windows'ta link oluşturmak yetki gerektiriyor, bu yüzden link testleri link kurulamazsa `skip` edilir.
- **K9 — Yalnızca kök `.gitignore`,** git stilinde desen eşleştirme. `.git/info/exclude` ve global gitignore dikkate alınmaz; iç içe `.gitignore` sonraki iterasyona.
  Gerekçe: temiz bir klonda iç içe gitignore'un etkisi büyük ihtimalle yok; gerekirse ölçüp ekleriz.
- **K10 — Kök yol yok ya da klasör değilse exception.** Tek bir dosya okunamıyorsa `UNREADABLE` ile dışlanır, tarama devam eder.
  Gerekçe: yanlış kök programcı hatasıdır; tek dosyanın sorunu taramayı durdurmamalı.

### Veri modeli

- **İki kayıt tipi:** `IncludedFile` (`path`, `size_bytes`, `is_test`) ve `ExcludedFile` (`path`, `reason`, `size_bytes`).
  Gerekçe: tek tipte `reason`, `is_test` ve `size_bytes` alanları duruma göre `None` olurdu ve geçersiz kombinasyonlar yazılabilirdi.
- **`ExcludedFile` kuralı `__post_init__` ile zorlanır:** `size_bytes` yalnızca `TOO_LARGE` için zorunlu; `SYMLINK`, `GITIGNORED`, `UNREADABLE` için `None`. İhlal `ValueError`.
  Gerekçe: boyut ölçülmeden verilen kararda "ölçmediğimizi kaydetmeyelim"; geçersiz kayıt hiç oluşamasın.
- **`ExclusionReason` bir `StrEnum`, 4 üye, kontrol sırasıyla:** `SYMLINK`, `GITIGNORED`, `TOO_LARGE`, `UNREADABLE`. `TEST_FILE` ve `EXCLUDED_DIR` yok (K4, K3).
- **`@dataclass(frozen=True, slots=True)`, koleksiyonlar `tuple`.** Gerekçe: `frozen` yalnızca yeniden atamayı engeller, gerçek değişmezlik için tuple gerekir. Pydantic bu aşamada gereksiz ağır; serileştirme gerekince (API sprint'i) düşünülür.
- **Yollar repo köküne göreli ve `/` ayraçlı,** çıktı `/` ayraçlı string üzerinde Python'un varsayılan karşılaştırmasıyla sıralı, locale yok.
  Gerekçe: Windows/Linux farkı determinizmi bozar; chunk ID'leri bu yoldan türeyecek. Sıralama testi `a.py` < `a/z.py` ikilisini kullanır (`.` < `/`), dizin dizin gezme sırasına güvenilmediğini kanıtlar.
- **`pruned_dirs` ad değil göreli yol:** kökteki `scripts/` ile `pkg/scripts/` ayırt edilebilsin.
- **`largest(n=5)`:** dahil + `TOO_LARGE` dosyalar arasından `(path, size_bytes)` çiftleri; boyuta göre azalan, eşitlikte path'e göre artan. `n=0` boş, `n<0` `ValueError`. Eşiği veriyle doğrulamak için `TOO_LARGE` dosyalar da görünmeli.
- **`exclusion_counts`:** `ExclusionReason` sırasını koruyan `Mapping`, sıfırlar dahil.
- **`ScanResult` koleksiyonları sıralamaz ve sıralı olduğunu doğrulamaz;** sıralama tarayıcının sorumluluğu. Yalnızca `largest` kendi sıralamasını yapar.

### Yardımcılar ve `scan()`

- **`load_gitignore`:** `pathspec.GitIgnoreSpec` (git'in kenar durumlarını `gitwildmatch` fabrikasından daha doğru taklit eder). Dosya yoksa boş spec; başka okuma hataları yukarı çıkar (yapılandırma hatası). `is_gitignored` sarmalayıcısı yok, `scan()` `spec.match_file(rel)` çağıracak.
- **Gitignore'lu klasörler budanmaz;** içindeki dosyalar tek tek `GITIGNORED` olur (K3 yalnızca sabit liste için). Testle sabitlendi (c2b).
- **Kural sırası tek yerde:** dosya başına karar `_classify_file` içinde, ilk eşleşen kazanır (K1). `SYMLINK` kontrolü `Path.is_symlink()` ile (lstat tabanlı, hedefe dokunmaz); kırık linkler çökmeden `SYMLINK` olur. `GITIGNORED` kararı boyut ölçülmeden verilir, bu yüzden `size_bytes=None`.
- **`scan()` içinde `max_file_size_bytes <= 0` için `ValueError`** (testli). Gerekçe: `scan()` `Settings` dışında da çağrılıyor; `Settings.gt=0` yetmez.
- **`UNREADABLE` = `stat` hatası + `open(..., "rb")` denemesi.** Gerekçe: tarayıcı içerik okumadığı için yalnızca `stat` hatası pratikte neredeyse hiç tetiklenmez; açma denemesi izin hatalarını yakalar. Testte `monkeypatch` ile `PermissionError` (Windows'ta izin kaldırarak test güvenilir değil).
- **Windows junction sınırı:** `os.walk` junction'ları symlink saymayabilir; kodda yorum olarak belirtildi, ayrıca ele alınmayacak (FastAPI klonunda beklenmiyor).
- **Python sürümü `>=3.12`:** `uv` ve ruff hedefi 3.12'ye çekildi. Ruff formatter parantezsiz `except A, B:` yazımını 3.14 hedefinde kendisi üretiyor ama 3.12 hedefinde geri çevirmiyor; satır elle `except (OSError, NotImplementedError):` yapıldı (parantezsiz yazım 3.12'de sözdizimi hatası).

### c2 için kayıtlı karar
- **`os.walk`'un listeleyemediği klasörler `ScanResult.unreadable_dirs` alanına yazılacak.**
  Gerekçe: `os.walk` varsayılan olarak listelenemeyen alt dizinleri sessizce atlar; bu K10'daki "tek dosya okunamıyor" durumundan farklı ve sessiz kalması içeriğin eksik indekslenmesi demek. Dosya kaydı (`ExcludedFile`) üretmiyoruz çünkü içindeki dosyaları bilmiyoruz; ayrı bir alan hem özette gösterilebilir hem testlenebilir.
  Biçim: `pruned_dirs` gibi göreli, `/` ayraçlı, sıralı `tuple[str, ...]`; `os.walk(onerror=...)` ile toplanır. **Uygulandı (c2a).** Alan zorunlu (varsayılansız): yeni bir `ScanResult` kuran herkes bunu bilerek vermeli; test yardımcısı `make_result` güncellendi.
  Kenar durum kararı: **kökün kendisi listelenemezse** `OSError` yukarı çıkar (K10 ile aynı mantık: erişilemeyen kök çağıran tarafın sorunu, "eksik ama devam" sayılmaz). Testte `os.scandir` `monkeypatch` ile `PermissionError` fırlatacak şekilde değiştirilir (Windows'ta izin kaldırmak güvenilir değil).

## Doğrulama
- `uv run python -m pytest`: **93 passed, 0 skipped** (c2b sonrası, 2026-11-25).
- `uv run python -m ruff check .` ve `uv run python -m ruff format --check .`: temiz.
- **Symlink testi:** `test_scan_does_not_follow_directory_symlinks` ilk çalıştırmada bu makinede atlanmıştı (link oluşturulamadı). Geliştirici Modu açıldıktan sonra atlanmadan çalıştı ve geçti: klasör linkleri gezilmiyor ve kayıt üretmiyor (K8 madde 6).
- **Python 3.12 ile test: ÇALIŞTIRILAMADI.** `uv run --python 3.12 python -m pytest` için uv CPython 3.12.15'i indirdi ama Windows Uygulama Denetimi yorumlayıcıyı engelledi (`os error 4551`, `Failed to spawn: python`). CLAUDE.md ilkeyi başka yolla aşmayı yasakladığı için denenmedi. Proje `.venv`'inin bozulmaması için deneme ayrı bir ortam dizininde yapıldı; `.venv` ve `uv.lock` değişmedi.
  Dolaylı kanıt: `ruff check --target-version py312` temiz (ruff, hedef sürümde geçersiz sözdizimini hata olarak bildirir). Bu bir test çalıştırması değildir; 3.12'de davranış doğrulanmış sayılmaz.
- c2'deki symlink testleri de aynı koşula bağlı: link kurulamayan ortamda `skip` olacak.

## Açık işler
1. **c2:** `scan()` içinde symlink → gitignore → boyut → okunamaz kontrolleri, öncelik testleri (symlink + gitignored → `SYMLINK`; gitignored + büyük → `GITIGNORED`; büyük + okunamaz → `TOO_LARGE`), eşik sınırı (`==` dahil, `+1` `TOO_LARGE`), `unreadable_dirs`.
2. **Eşiği veriyle doğrula:** gerçek FastAPI klonunda `largest()` çıktısına bak; çekirdek dosyalar (`applications.py`, `routing.py`) 500 KB altında kalıyor mu?
3. **Gerçek repoda duman testi:** `data/repos/fastapi` üzerinde tarama; sayılar mantıklı mı (dahil, test, `GITIGNORED`, budanan klasörler).
4. **CLI özeti:** `index` komutunda tarama özeti (gerekçe sayıları, `pruned_dirs`, `unreadable_dirs`, en büyük 5 dosya).
5. İç içe `.gitignore`: gerekirse ölçüp sonraki iterasyona.
6. **Python 3.12 testleri:** App Control 3.12 yorumlayıcısını engelliyor; ya ilke bu yorumlayıcıya izin verecek şekilde güncellenmeli ya da testler CI'da (ör. GitHub Actions) 3.12 ile koşturulmalı. O zamana kadar `requires-python >=3.12` iddiası doğrulanmamıştır.

## Hakimiyet soruları
- `os.walk`'ta `dirnames[:] = kept` neden `dirnames = kept` değil?
- Sıralamayı neden walk sırasına bırakmayıp `/` ayraçlı string üzerinden yapıyoruz? (`a.py` ve `a/z.py` örneği)
- `frozen=True` neden tek başına gerçek değişmezlik sağlamaz?
- `UNREADABLE` için neden yalnızca `stat` yetmiyor?
