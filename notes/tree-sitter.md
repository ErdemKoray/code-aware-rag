# tree-sitter node rehberi (Python)

Bu belge, S03'teki chunker'ı yazarken "hangi node nerede, hangi alanda duruyor?" sorusunu cevaplamak için var.
Her bilgi **gözlemden** geliyor, hafızadan değil.

**Dayanak:** `tree-sitter` 0.27.0, `tree-sitter-python` 0.25.0. Sayımlar, FastAPI 0.143.0'ın `git ls-files "*.py"` ile listelenen
**1167 dosyasının** hepsinin ayrıştırılmasından çıktı (2026-11-26). Küçük örnekler, `parse()` ile elle çalıştırıldı.
FastAPI'de hiç geçmeyen bir yapı varsa bunu ayrıca yazdım ("FastAPI'de görülmedi").

## 1. Temel kavramlar (sade anlatım)

| Kavram | Ne demek |
|---|---|
| **node** | Ağaçtaki her düğüm. Bir kaynak parçasını (`def f(): ...` gibi) temsil eder. |
| **tip (`node.type`)** | Düğümün türü: `function_definition`, `identifier`, `block` ... |
| **named / anonymous** | `named`: gramerde adı olan düğüm (`identifier`, `call`). `anonymous`: sadece yazım işareti (`def`, `:`, `(`, `,`, `async`). `node.is_named` ile ayrılır. |
| **çocuk** | Bir düğümün içindeki düğümler. `node.children` hepsini, `node.named_children` yalnızca named olanları verir. |
| **alan (field)** | Bir çocuğa verilen **rol adı**. Örneğin bir fonksiyonun `name` alanı onun adı olan `identifier`'dır. `node.child_by_field_name("name")` ile alınır. Alan adı ile çocuğun **tipi** farklı şeylerdir: `body` alanının tipi `block`. |
| **`ERROR` / `MISSING`** | Hatalı kaynakta ağaca eklenen özel düğümler. `ERROR`: ayrıştırılamayan parça. `MISSING`: parser'ın "burada olmalıydı" diye uydurduğu sıfır genişlikli jeton. `has_error`, ikisinden biri varsa `True` olur. |
| **satır/sütun** | `start_point`/`end_point` `(row, column)` verir. `row` **0 tabanlı**, `end_point` **dışlayıcı**. Bizim `line_range()` bunu 1 tabanlı, kapsayıcı satıra çevirir (bkz. bölüm 8). |
| **bayt konumu** | `start_byte`/`end_byte`: kaynak `bytes` içindeki konum. `column` da bayttır, karakter değildir. Metin için `source[start_byte:end_byte]` kullanılır. |

## 2. Beklentiden farklı çıkanlar (özet)

Sprint kapsamındaki alan listesi (`name`, `parameters`, `body`, `decorator`) ve gramer bilgisi, şu varsayımlara yol açabilir. Aşağıdaki
yedi maddenin hepsi gözlemle **tutmadı** ya da düzeltilmesi gerekti (2. ve 3. madde doğrudan o listeden kaynaklanıyor):

| # | Beklenti | Gözlem |
|---|---|---|
| 1 | `async def` ayrı bir node tipi | **Değil.** Tip yine `function_definition`. İlk çocuğu anonim bir `async` jetonu. FastAPI'de 5280 fonksiyonun 1070'i async. |
| 2 | `decorator` bir alan adı | **Değil.** `decorator` bir **çocuk node tipi**. `decorated_definition`'ın alanı yalnızca `definition`. Birden çok decorator olabilir; hepsi alansız çocuktur. `child_by_field_name("decorator")` → `None`. |
| 3 | Tüm parametrelerde `name` alanı | **Hayır.** `typed_parameter`'ın (`b: int`) yalnızca `type` alanı var; adı alansız bir `identifier` çocuğu. `default_parameter` ve `typed_default_parameter`'da `name` alanı var. Ad çıkaran kod parametre türüne göre dallanmalı. |
| 4 | Docstring için ayrı node | **Yok.** Docstring, gövdenin ilk `expression_statement`'ının içindeki bir `string`. Bunu "ilk ifade bir string mi?" diye kendimiz anlamalıyız. |
| 5 | Yorumlar yalnızca `block` içinde | **Hayır.** `comment` neredeyse her yerde çocuk olabilir (bölüm 5). |
| 6 | Gövdesiz tanım hata verir | **Vermez.** `def f():` ve `class A:` (gövdesiz) için `has_error=False`; `body` alanı sıfır genişlikli boş bir `block`. `has_error` bu durumu yakalamaz. |
| 7 | Eğitim örneği dosyalarında (`docs_src/`) en az bir `ERROR`/`MISSING` çıkar | **Çıkmadı.** 1167 dosyanın hiçbirinde yok; gramer FastAPI'nin tüm yazımını tanıyor. |

## 3. Tanımlar

### `function_definition` (5280 adet; metot ve iç içe fonksiyonlar dahil)

| Alan | Çocuğun tipi | Gözlenen sayı | Not |
|---|---|---|---|
| `name` | `identifier` | 5280 | Her zaman var. |
| `parameters` | `parameters` | 5280 | Her zaman var. |
| `body` | `block` | 5280 | Her zaman var. |
| `return_type` | `type` | 1023 | Yalnızca `-> ...` varsa. |

Alansız çocuklar: anonim `def` (5280), `:` (5280), `async` (1070), `->` (1023); named olarak `comment` (148, bkz. bölüm 5).
`type_parameters` alanı (PEP 695, `def f[T](...)`) gramerde var (kendi örneğimde doğruladım) ama **FastAPI'de görülmedi**.

### `class_definition` (725 adet)

| Alan | Çocuğun tipi | Gözlenen sayı | Not |
|---|---|---|---|
| `name` | `identifier` | 725 | |
| `superclasses` | `argument_list` | 628 | Taban sınıflar `argument_list` içinde; `metaclass=...` gibi anahtar argümanlar da burada. Yoksa alan hiç yok. |
| `body` | `block` | 725 | |

Alansız çocuklar: anonim `class` ve `:` (725'er), named `comment` (15). `type_parameters` FastAPI'de görülmedi.

### `decorated_definition` (2387 adet; 2043'ü modül düzeyinde)

| Alan | Çocuğun tipi | Gözlenen sayı |
|---|---|---|
| `definition` | `function_definition` | 2362 |
| `definition` | `class_definition` | 25 |

Alansız çocuklar: bir ya da daha fazla `decorator` (toplam 2436) ve araya girmiş `comment` (2). Yani **decorator'lar tanımın
dışında, sarmalayıcıda durur**: bir `function_definition`'ın kendisi decorator'ını bilmez. Bir fonksiyonun satır aralığını
decorator dahil almak için sarmalayıcıyı (`decorated_definition`) kullanmak gerekir; `line_range()` bunu doğru verir
(`@a\n@b\ndef f(): ...` için sarmalayıcı 1-4, içindeki `function_definition` 3-4).

### `decorator` (2436 adet)

Alanı yok. `@` jetonundan sonra tek bir ifade çocuğu var:

| Çocuk tipi | Sayı | Örnek |
|---|---|---|
| `call` | 2263 | `@app.get("/x")` |
| `identifier` | 153 | `@staticmethod` |
| `attribute` | 20 | `@functools.wraps` gibi çağrısız noktalı ad |
| `comment` | 9 | `@dec  # not` satırındaki yorum decorator'ın içine girer |

## 4. Parametreler

`parameters` düğümü `(`, `)` ve `,` anonim jetonlarının arasında şu named çocukları içerir:

| Çocuk tipi | Sayı | Anlamı | Ad nereden alınır |
|---|---|---|---|
| `typed_parameter` | 3120 | `b: int`, `*args: str`, `**kw: int` | Alansız `identifier` çocuğu (alanı yalnızca `type`). `*args`/`**kw` ise `list_splat_pattern` / `dictionary_splat_pattern` çocuğu. |
| `typed_default_parameter` | 1814 | `d: int = 2` | `name` alanı; ayrıca `type` ve `value` alanları. |
| `identifier` | 894 | tipsiz, varsayılansız `a` | Düğümün kendisi. |
| `keyword_separator` | 176 | çıplak `*` | Ad yok. |
| `default_parameter` | 38 | `c=1` | `name` alanı; `value` alanı. |
| `comment` | 15 | parametreler arasındaki yorum | Parametre değil, atlanmalı. |
| `dictionary_splat_pattern` | 10 | tipsiz `**kw` | |
| `list_splat_pattern` | 9 | tipsiz `*args` | |
| `positional_separator` | 5 | `/` | Ad yok. |

`lambda` farklı: `parameters` alanında `lambda_parameters` tipi çıkar (23 adet), gövde `body` alanında.

## 5. Gövde, yorumlar ve docstring

- **`block`**: bir `if`/`def`/`class` gövdesi. Çocukları ifadeler (en sık: `expression_statement` 10823, `assert_statement` 5550,
  `return_statement` 2459, `if_statement` 1139) ve iç içe `function_definition` (519), `decorated_definition` (344),
  `class_definition` (89). Bir sınıfın metotları, sınıfın `body` bloğunun çocuklarıdır (iç içe sınıf ve metot testle sabitli).
- **`comment`** her yerde olabilen "ekstra" bir düğümdür. FastAPI'de şu ebeveynlerin altında görüldü:

  | Ebeveyn | Sayı | Nasıl oluşur |
  |---|---|---|
  | `block` | 534 | gövde içindeki yorum satırı |
  | `function_definition` | 148 | `def f():  # yorum` satır sonu yorumu, `:` ile gövde `block`'u arasına girer |
  | `if_statement` | 55 | |
  | `class_definition` | 15 | |
  | `parameters` | 15 | |
  | `decorator` | 9 | `@dec  # yorum` |
  | `import_from_statement` | 6 | |
  | `try_statement` | 5 | |
  | `decorated_definition` | 2 | decorator ile `def` arasındaki yorum satırı |

  Sonuç: "yorum" tek bir yerde aranmaz; ayrıca modül düzeyindeki yorumlar (326 adet) üst düzey node'tur.
- **Docstring:** `block`'un ilk çocuğu `expression_statement` ve onun içindeki `string` ise docstring'dir.
  `string` düğümü `string_start`, `string_content`, `string_end` (ve f-string'lerde `interpolation`) çocuklarından oluşur.
  Örnek: `def f():\n    """Doc."""\n    return 1` → `block` içinde `expression_statement > string`, sonra `return_statement`.

## 6. Modül düzeyi

`module` kök düğümdür. FastAPI'nin 1167 dosyasında doğrudan çocuk olarak görülen tipler:

| Tip | Sayı |
|---|---|
| `import_from_statement` | 3020 |
| `function_definition` | 2399 |
| `decorated_definition` | 2043 |
| `expression_statement` | 1367 |
| `import_statement` | 680 |
| `class_definition` | 611 |
| `comment` | 326 |
| `if_statement` | 23 |
| `try_statement` | 18 |
| `with_statement` | 3 |
| `future_import_statement` | 3 |
| `for_statement` | 2 |

Alan adı yok; sıra kaynak sırasıdır. `if_statement` (alanlar: `condition`, `consequence`, `alternative` → `else_clause`/`elif_clause`) ve
`try_statement` (alan: `body`; `except_clause`, `finally_clause`, `else_clause` alansız çocuk) modül düzeyinde **tanım içerebilir**:
örnek `try:\n    def g(): ...\nexcept ImportError:\n    pass` → `function_definition`, `try_statement > body: block` içinde. Bu 23 + 18 node'un
içinde kaç tanım olduğu **ölçülmedi**; S03'te bilinmesi gereken bir soru.

## 7. İfade düğümleri (çağrı ve import ilişkileri için)

| Tip | Alanlar (gözlenen çocuk tipleri) |
|---|---|
| `call` | `function`: `attribute` (10644), `identifier` (8326), `call` (13), `subscript` (8); `arguments`: `argument_list` (18907), `generator_expression` (84) |
| `attribute` | `object`: `identifier` (16880), `attribute` (1217), `call` (543), ...; `attribute`: `identifier` |
| `assignment` | `left`: `identifier` (8681), `attribute` (364), `subscript` (298), `pattern_list` (170), `tuple_pattern` (52); `right`: `call` (6069) en yaygın; `type`: `type` (1605, tip ek açıklamalı atamalarda) |
| `import_statement` | `name`: `dotted_name` (703) |
| `import_from_statement` | `module_name`: `dotted_name` (3015) ya da `relative_import` (211, `from . import x`); `name`: `dotted_name` (4316) ya da `aliased_import` (142) |
| `keyword_argument` | (6631 adet) `name`: `identifier` (6631); `value`: `identifier` (2439), `string` (1525), `dictionary` (785), `list` (499), ... |
| `except_clause` | `value`: `identifier` (42), `as_pattern` (23), `attribute` (10), `tuple` (4); gövde alansız `block` |

`future_import_statement` (`from __future__ import ...`) `import_from_statement`'tan **ayrı bir tiptir** (3 adet, hepsi modül düzeyinde).

## 8. Satır aralıkları (`line_range`) ve sınır durumları

- tree-sitter satırları 0 tabanlı, bitiş noktası dışlayıcıdır. `line_range()` 1 tabanlı, kapsayıcı `(ilk, son)` verir.
- **Sütun 0'da biten node'lar:** bir node sonraki satırın 0. sütununda bitiyorsa o satırı kapsamaz; yardımcı `son = end_row` döndürür.
  - Kök `module` her zaman son satırdan sonra `(n, 0)`'da biter (`def f():\n    pass\n` → `module` 1-2).
  - FastAPI'de kök dışı **29 node** bu durumda ve hepsi `string_content`: kapanış `"""`'ı satır başında olan çok satırlı string'lerin içeriği.
    `string_content` 1-2 satırı, ait olduğu `string` 1-3 satırı verir.
  - `line_continuation` (`x = 1 \` + satır sonu) aynı biçimde biter; testle sabitli.
- **Boş modül:** `module` `(0,0)-(0,0)`, yani `line_range` → `(1, 1)`.
- **Sonda yeni satır yok:** `def f():\n    pass` → `module` 1-2.
- **CRLF:** `\r\n` kaynaklar LF ile aynı ağacı üretir.
- Alınan ders: "son satır = `end_point.row + 1`" kuralı tek başına yanlış sonuç verirdi; tüm `dosya:satır` atıfları `line_range()` üzerinden gitmeli.

## 9. Hata durumu

- `parse()` hatalı kaynakta **istisna fırlatmaz**; ağaç yine kurulur, `has_error` `True` olur.
- `def f(:\n    pass\n\nclass B:\n    x = 1\n` → `function_definition` (içinde sıfır genişlikli `MISSING` `)`) ve ondan sonraki
  `class_definition` korunur: parser toparlanır, hasar yerel kalır.
- `x = (1, 2\n` → üst düzeyde tek bir `ERROR` node'u (ayrıştırılamayan tüm ifadeyi sarar).
- Geçerli Python'da `has_error` hiç `True` olmadı: FastAPI'nin 1167 dosyasında 0 hata.
- Uyarı (bölüm 2, madde 6): `def f():` gibi gövdesiz tanımlar hata sayılmaz. `has_error=False`, "kod geçerli" demek değildir.
- Girdi UTF-8 varsayılır; geçersiz UTF-8 baytları da istisna üretmez (testle sabitli).

## 10. Bu çalışmada gözlenen tüm named node tipleri (101)

`aliased_import`, `argument_list`, `as_pattern`, `as_pattern_target`, `assert_statement`, `assignment`, `attribute`,
`augmented_assignment`, `await`, `binary_operator`, `block`, `boolean_operator`, `break_statement`, `call`, `class_definition`,
`comment`, `comparison_operator`, `concatenated_string`, `conditional_expression`, `continue_statement`, `decorated_definition`,
`decorator`, `default_parameter`, `delete_statement`, `dictionary`, `dictionary_comprehension`, `dictionary_splat`,
`dictionary_splat_pattern`, `dotted_name`, `elif_clause`, `ellipsis`, `else_clause`, `escape_interpolation`, `escape_sequence`,
`except_clause`, `expression_list`, `expression_statement`, `false`, `finally_clause`, `float`, `for_in_clause`, `for_statement`,
`function_definition`, `future_import_statement`, `generator_expression`, `generic_type`, `global_statement`, `identifier`,
`if_clause`, `if_statement`, `import_from_statement`, `import_prefix`, `import_statement`, `integer`, `interpolation`,
`keyword_argument`, `keyword_separator`, `lambda`, `lambda_parameters`, `list`, `list_comprehension`, `list_splat`,
`list_splat_pattern`, `module`, `named_expression`, `none`, `nonlocal_statement`, `not_operator`, `pair`, `parameters`,
`parenthesized_expression`, `pass_statement`, `pattern_list`, `positional_separator`, `raise_statement`, `relative_import`,
`return_statement`, `set`, `set_comprehension`, `slice`, `string`, `string_content`, `string_end`, `string_start`, `subscript`,
`true`, `try_statement`, `tuple`, `tuple_pattern`, `type`, `type_conversion`, `type_parameter`, `typed_default_parameter`,
`typed_parameter`, `unary_operator`, `union_type`, `while_statement`, `with_clause`, `with_item`, `with_statement`, `yield`.

Gramerde olup FastAPI'de **görülmeyenler** (kendi örneklerimde doğruladıklarım): `type_alias_statement` (`type X = int`, alanlar `left`/`right`)
ve `function_definition`/`class_definition` üzerindeki `type_parameters` alanı. `match_statement` gibi diğer yapılar bu çalışmada denenmedi.

## 11. S03 için kısa kontrol listesi

1. Bir tanımın metnini/satırını alırken `decorated_definition` varsa **onu** kullan (decorator'lar sarmalayıcıda).
2. Ad almak için: `function_definition`/`class_definition` → `child_by_field_name("name")`. Parametre adı için tipe göre dallan.
3. `async` kontrolü: `function_definition.children[0].type == "async"`.
4. `comment` her yerde çıkabilir; "ilk çocuk" ya da "n. çocuk" varsayımı yapma, `named_children`'ı tipe göre süz.
5. Docstring: `body` içindeki ilk `expression_statement > string`.
6. Modül düzeyindeki `if_statement` / `try_statement` içindeki tanımlar için bir karar gerek (bölüm 6).
7. Tüm `dosya:satır` değerleri `parsing.python.line_range()` üzerinden.
