package protocol

import "testing"

func TestParseTFHKA(t *testing.T) {
	type tc struct {
		in      string
		wantTyp string
		wantPar []any
		wantErr string
	}
	cases := []tc{
		{"", "", nil, ""},
		{"   ", "", nil, ""},
		{"S1", "S1", nil, ""},
		{"S8P", "S8P", nil, ""},
		{" S5 ", "S5", nil, ""},
		{"U0X", "U0X", nil, ""},
		{"U1Z", "U1Z", nil, ""},
		{"3", "SUBTOTAL_PRINT", nil, ""},
		{"4", "SUBTOTAL_SILENT", nil, ""},
		{"101", "CLOSE_TOTALIZE", nil, ""},
		{"0", "OPEN_DRAWER", nil, ""},
		{"d1", "OPEN_CREDIT_NOTE", nil, ""},
		{"d2", "OPEN_DEBIT_NOTE", nil, ""},
		{"d11 10.000 x", "ITEM_CREDIT", []any{1}, ""},
		{"d25 10.000 x", "ITEM_CREDIT", []any{2}, ""},
		{"dx", "UNKNOWN", []any{"dx"}, ""},
		{"`0abc", "ITEM_DEBIT", []any{0}, ""},
		{"`abc", "ITEM_DEBIT", []any{1}, ""},
		{"@COMENTARIO  hola  ", "COMMENT", []any{"hola"}, ""},
		{"@COMENTARIO", "COMMENT", []any{""}, ""},
		{"!   2.000     15.00 CAFE", "ITEM", []any{1}, ""},
		{"\"   3.000      8.00 PAN", "ITEM", []any{2}, ""},
		{"#   1.000      1.00 X", "ITEM", []any{3}, ""},
		{"80$", "OPEN_NON_FISCAL", nil, ""},
		{"81", "CLOSE_NON_FISCAL", nil, ""},
		{"80!texto", "PRINT_NON_FISCAL_TEXT", []any{"texto"}, ""},
		{"80*contenido", "PRINT_NON_FISCAL_CONTENT", []any{"contenido"}, ""},
		{"10054.00", "PAYMENT", []any{"54.00"}, ""},
		{"1030.00", "PAYMENT_DESC", []any{"0.00"}, ""},
		{"7005.00", "DISCOUNT", []any{"5.00"}, ""},
		{"7012.00", "SURCHARGE", []any{"2.00"}, ""},
		{"iR*J-12345678-9", "CUSTOMER_RIF", []any{"J-12345678-9"}, ""},
		{"iS*EMPRESA", "CUSTOMER_NAME", []any{"EMPRESA"}, ""},
		{"i01Calle 1", "CUSTOMER_ADDRESS", []any{"Calle 1"}, ""},
		{"i020123", "CUSTOMER_PHONE", []any{"0123"}, ""},
		{"iF*0001", "INVOICE_NUMBER", []any{"0001"}, ""},
		{"iD*01/01/26", "INVOICE_DATE", []any{"01/01/26"}, ""},
		{"iI*ABC", "FISCAL_SERIAL", []any{"ABC"}, ""},
		{"  iR*  J-1 ", "CUSTOMER_RIF", []any{"  J-1"}, ""},
		{"zzz", "UNKNOWN", []any{"zzz"}, ""},
		{"d1", "OPEN_CREDIT_NOTE", nil, ""},
	}
	for _, c := range cases {
		typ, par, err := ParseTFHKA(c.in)
		if c.wantErr != "" {
			if err == nil || err.Error() != c.wantErr {
				t.Errorf("ParseTFHKA(%q) err = %v, want %q", c.in, err, c.wantErr)
			}
			continue
		}
		if err != nil {
			t.Errorf("ParseTFHKA(%q) unexpected err: %v", c.in, err)
			continue
		}
		if typ != c.wantTyp {
			t.Errorf("ParseTFHKA(%q) type = %q, want %q", c.in, typ, c.wantTyp)
		}
		if !equalParams(par, c.wantPar) {
			t.Errorf("ParseTFHKA(%q) params = %#v, want %#v", c.in, par, c.wantPar)
		}
	}
}

func TestParseTFHKAItemCreditError(t *testing.T) {
	_, _, err := ParseTFHKA("d²abc")
	if err == nil || err.Error() != "invalid literal for int() with base 10: '²'" {
		t.Errorf("err = %v", err)
	}
}

func TestParseIxBatch(t *testing.T) {
	typ, par, ok := ParseIxBatch("@PrintLine|CAFE|2|15.00|general")
	if !ok || typ != "@PrintLine" || len(par) != 4 || par[0] != "CAFE" || par[4-1] != "general" {
		t.Errorf("got %q %#v %v", typ, par, ok)
	}
	typ, par, ok = ParseIxBatch("@Status")
	if !ok || typ != "@Status" || par != nil {
		t.Errorf("got %q %#v %v", typ, par, ok)
	}
	typ, _, ok = ParseIxBatch("no-at")
	if ok || typ != "" {
		t.Errorf("got %q %v", typ, ok)
	}
	_, par, ok = ParseIxBatch("@X| a | b ")
	if !ok || par[0] != "a" || par[1] != "b" {
		t.Errorf("got %#v", par)
	}
}

func TestFormatLineItem(t *testing.T) {
	got := FormatLineItem("!", 2, 15, "CAFE")
	want := "!   2.000     15.00CAFE"
	if got != want {
		t.Errorf("FormatLineItem = %q, want %q", got, want)
	}
	got = FormatCreditNoteItem(1, 3, 8.5, "PAN")
	want = "d1   3.000      8.50PAN"
	if got != want {
		t.Errorf("FormatCreditNoteItem = %q, want %q", got, want)
	}
	got = FormatDebitNoteItem(2, 1, 100, "X")
	want = "`2   1.000    100.00X"
	if got != want {
		t.Errorf("FormatDebitNoteItem = %q, want %q", got, want)
	}
}

func TestLineItemPrefix(t *testing.T) {
	cases := []struct {
		rate float64
		want string
	}{
		{0, " "},
		{8, "\""},
		{11, "\""},
		{12, "!"},
		{15, "!"},
		{16, "#"},
		{31, "#"},
	}
	for _, c := range cases {
		if got := LineItemPrefix(c.rate); got != c.want {
			t.Errorf("LineItemPrefix(%v) = %q, want %q", c.rate, got, c.want)
		}
	}
}

func TestGetStatusByte(t *testing.T) {
	cases := []struct {
		mode, state, memory string
		want                byte
	}{
		{"test", "waiting", "ok", 0x01},
		{"test", "fiscal", "ok", 0x02},
		{"test", "non_fiscal", "ok", 0x03},
		{"fiscal", "waiting", "ok", 0x04},
		{"fiscal", "fiscal", "ok", 0x05},
		{"fiscal", "non_fiscal", "ok", 0x06},
		{"fiscal", "waiting", "almost_full", 0x07},
		{"fiscal", "fiscal", "almost_full", 0x08},
		{"fiscal", "non_fiscal", "almost_full", 0x09},
		{"fiscal", "waiting", "full", 0x0A},
		{"fiscal", "fiscal", "full", 0x0B},
		{"fiscal", "non_fiscal", "full", 0x0C},
		{"fiscal", "other", "ok", 0x04},
		{"test", "other", "ok", 0x04},
	}
	for _, c := range cases {
		if got := GetStatusByte(c.mode, c.state, c.memory); got != c.want {
			t.Errorf("GetStatusByte(%q,%q,%q) = 0x%02X, want 0x%02X", c.mode, c.state, c.memory, got, c.want)
		}
	}
}

func equalParams(a, b []any) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
