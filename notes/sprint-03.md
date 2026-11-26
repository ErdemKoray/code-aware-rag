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

## Kararlar ve gerekçeleri
- **Kodu Claude yazar** (çekirdek mantık dahil). Sprint başında plan ve tasarım kararları sunulur, onaydan sonra her adımda
  `pytest`, `ruff check`, `ruff format --check` geçerse commit edilip devam edilir; kapsanmayan bir tasarım kararında durulur.
  Gerekçe: eski "learning project" kuralları çalışma moduyla çelişiyordu ve chunker çekirdek mantık.
- **Repo dışı dosya kuralı:** araç önbellekleri (uv, ruff, pytest) ve pytest geçici klasörleri istisna; geçici betikler ve
  çıktıları `data/out/` altında (gitignore'da). Gerekçe: önceki kural pratikte uygulanamıyordu.

- **Pin testi (P7):** `git -C`, kendi `.git`'i olmayan bir dizinde sessizce üstteki (bu) repoyu cevapladığı için test
  "klon yok" ölçütü olarak `.git` varlığına bakar. Git komutları `--no-optional-locks` ile çalışır, hedef repoya hiçbir şey yazmaz.
  Test geçiyor, klon gizliyken atlanıyor ve yanlış SHA verildiğinde başarısız oluyor (üçü de elle doğrulandı).

## Açık işler
(plan onayından sonra güncellenecek)
