package pyfmt

import (
	"math"
	"testing"
)

func TestPyRoundMatchesPythonTies(t *testing.T) {
	cases := []struct {
		x    float64
		nd   int
		want float64
	}{
		{2.675, 2, 2.67},
		{0.125, 2, 0.12},
		{0.135, 2, 0.14},
		{1.005, 2, 1.0},
		{2.345, 2, 2.35},
		{10.015, 2, 10.02},
		{0.005, 2, 0.01},
		{15.5, 0, 16.0},
		{12.5, 0, 12.0},
		{2.5, 0, 2.0},
		{-0.125, 2, -0.12},
		{1.0449999, 2, 1.04},
		{1.0, 0, 1.0},
	}
	for _, c := range cases {
		if got := PyRound(c.x, c.nd); got != c.want {
			t.Errorf("PyRound(%v, %d) = %v, want %v", c.x, c.nd, got, c.want)
		}
	}
}

func TestPyRoundSpecials(t *testing.T) {
	if !math.IsNaN(PyRound(math.NaN(), 2)) {
		t.Error("PyRound(NaN) should stay NaN")
	}
	if !math.IsInf(PyRound(math.Inf(1), 2), 1) {
		t.Error("PyRound(+Inf) should stay +Inf")
	}
}

func TestFloat(t *testing.T) {
	ok := []struct {
		in   string
		want float64
	}{
		{"1.5", 1.5},
		{" 1.5 ", 1.5},
		{"\t2\n", 2},
		{"1_0", 10},
		{"+.5", 0.5},
		{"5.", 5},
		{"-0.0", 0},
		{"1e400", math.Inf(1)},
		{"1e-400", 0},
		{"inf", math.Inf(1)},
		{"INF", math.Inf(1)},
		{"-Infinity", math.Inf(-1)},
		{"nan", math.NaN()},
		{"-1e3", -1000},
		{"1.2e-3", 0.0012},
	}
	for _, c := range ok {
		got, err := Float(c.in)
		if err != nil {
			t.Errorf("Float(%q) error: %v", c.in, err)
			continue
		}
		if math.IsNaN(c.want) {
			if !math.IsNaN(got) {
				t.Errorf("Float(%q) = %v, want NaN", c.in, got)
			}
		} else if got != c.want {
			t.Errorf("Float(%q) = %v, want %v", c.in, got, c.want)
		}
	}
	bad := []string{"0x10", "1_", "1__0", "1.2.3", "abc", " abc ", "1e", "5 5", "0b101"}
	for _, in := range bad {
		if _, err := Float(in); err == nil {
			t.Errorf("Float(%q) should fail", in)
		} else {
			want := "could not convert string to float: '" + in + "'"
			if err.Error() != want {
				t.Errorf("Float(%q) err = %q, want %q", in, err.Error(), want)
			}
		}
	}
}

func TestInt(t *testing.T) {
	ok := []struct {
		in   string
		want int
	}{
		{"5", 5},
		{" 5 ", 5},
		{"+5", 5},
		{"-12", -12},
		{"1_0", 10},
		{"007", 7},
		{"0", 0},
	}
	for _, c := range ok {
		got, err := Int(c.in)
		if err != nil || got != c.want {
			t.Errorf("Int(%q) = %v, %v; want %v", c.in, got, err, c.want)
		}
	}
	bad := []string{"5.0", "1e2", "²", "abc", " abc ", "", "1_", "1 2"}
	for _, in := range bad {
		if _, err := Int(in); err == nil {
			t.Errorf("Int(%q) should fail", in)
		} else {
			want := "invalid literal for int() with base 10: '" + in + "'"
			if err.Error() != want {
				t.Errorf("Int(%q) err = %q, want %q", in, err.Error(), want)
			}
		}
	}
}

func TestPyIsDigit(t *testing.T) {
	yes := []rune{'0', '9', '5', '\u0663', '\u0660', '\uff13', '\u00b2', '\u00b3', '\u00b9', '\u2070', '\u2074', '\u2079', '\u2080', '\u2089'}
	for _, r := range yes {
		if !PyIsDigit(r) {
			t.Errorf("PyIsDigit(%q) = false, want true", r)
		}
	}
	no := []rune{'a', ' ', '-', '.', '\u2071', '\u208a', '\u00bc'}
	for _, r := range no {
		if PyIsDigit(r) {
			t.Errorf("PyIsDigit(%q) = true, want false", r)
		}
	}
}
