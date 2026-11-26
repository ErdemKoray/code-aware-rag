# Sprint 03 — Yapı-farkında chunker

Branch: `sprint/s03-chunker` · Başlangıç: 2026-11-26

## Durum
S03 öncesi sağlık kontrolünün düzeltmeleri yapılıyor. Chunker planı henüz sunulmadı / onaylanmadı.

## S03 öncesi sağlık kontrolü

Kontrol hiçbir dosya değiştirilmeden yapıldı; bulgular P1–P13 olarak numaralandı. Sahibin kararlarıyla
her düzeltme grubu ayrı commit olarak uygulanıyor.

| Bulgu | Ne yapıldı | Commit |
|---|---|---|
| (ek) | Dependabot'un `actions/checkout` v6 → v7 PR'ı (#5) sahibi tarafından merge edildi | `0baf20a`, merge `95fe3a5` |
| P1–P3 | `CLAUDE.md`: sprint S03; "learning project" bölümü kaldırıldı; Working mode yenilendi; repo dışı dosya kuralına istisnalar | `chore: update claude instructions for sprint 03` |
| P5 | `pydantic` doğrudan bağımlılık olarak eklendi (`>=2.14.1`; kurulu sürüm zaten buydu) | `chore(deps): declare pydantic dependency` |
| P6 | `pyproject.toml` açıklaması yazıldı | `chore: describe the project in pyproject` |
| P7 | `tests/test_target_repo.py`: klonun `HEAD`'i ve tag'i config'deki SHA ile aynı; klon yoksa `skip` | `test(config): verify fastapi clone matches pinned version` |
| P8 | Kullanılmayan `noqa` kaldırıldı; ters yazılmış karşılaştırma `expected` değişkeniyle düzeltildi | `test: fix unused noqa and yoda condition` |
| P9 | `.env.example`, `.gitignore`, `.gitmessage`, `__main__.py` diskte LF'ye çevrildi (silip `git checkout --`; içerik aynı) | commit yok: indeks zaten LF idi, diff oluşmadı |
| P10 | Ruff: `extend-exclude = ["data/**"]`, `force-exclude = true`; `.gitignore`: `.env.*` (`.env.example` hariç). **Kısmi çözüm, aşağıya bak** | `chore: exclude data from ruff and ignore env variants` |
| P13 | CI: `push` yalnızca `main`; `timeout-minutes: 10`; `concurrency` (yalnızca PR çalışmaları iptal edilir, `main` çalışmaları tamamlanır); yanlış yorum düzeltildi. Yerelde çalıştırılamaz, doğrulaması PR'ın CI'ında | `ci: limit push trigger and add timeout and concurrency` |
| LICENSE | MIT, "Copyright (c) 2026 Erdem Koray" | `docs: add mit license` |
| P11 | README: durum ve roadmap, çalışan komutlar (`scan`, `parse-debug`), proje yapısı, düzeltilmiş clone/checkout komutları, Uygulama Denetimi notu, lisans. Komutlar standart biçimde (`uv run rag`, `uv run pytest`); bu biçimler bu makinede engelli olduğu için burada çalıştırılarak denenmedi | `docs: update readme` |
| P12 | Sprint notları: eski/çelişen cümleler düzeltildi, `sprint-00`'a "Açık işler", `sprint-02`'ye "Durum" ve "Hakimiyet soruları" açıldı. Mevcut hakimiyet sorularına dokunulmadı, hiçbirine cevap yazılmadı | `docs: tidy sprint notes` |

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

## Açık işler
1. P10'un kalan boşluğu: klona açık yolla ruff çalıştırmayı engellemek (seçenekler sahibine sunuldu).
2. S02 PR'ının (#4) CI sonucu teyit edilecek (ayrıntı `sprint-02.md` Açık işler 4).
