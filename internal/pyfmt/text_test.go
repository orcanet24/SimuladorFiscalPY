package pyfmt

import "testing"

func TestCenterMatrix(t *testing.T) {
	type tc struct {
		s     string
		width int
		want  string
	}
	cases := []tc{
		{"x", 4, " x  "},
		{"ab", 5, "  ab "},
		{"test", 11, "    test   "},
		{"x", 1, "x"},
		{"x", 2, "x "},
		{"x", 3, " x "},
		{"x", 5, "  x  "},
		{"x", 6, "  x   "},
		{"x", 7, "   x   "},
		{"ab", 2, "ab"},
		{"ab", 3, " ab"},
		{"ab", 4, " ab "},
		{"ab", 6, "  ab  "},
		{"ab", 7, "   ab  "},
		{"ab", 8, "   ab   "},
		{"abc", 4, "abc "},
		{"abc", 5, " abc "},
		{"abc", 6, " abc  "},
		{"abc", 7, "  abc  "},
		{"abc", 8, "  abc   "},
		{"abc", 9, "   abc   "},
		{"abcd", 4, "abcd"},
		{"abcd", 5, " abcd"},
		{"abcd", 6, " abcd "},
		{"abcd", 7, "  abcd "},
		{"abcd", 8, "  abcd  "},
		{"abcd", 9, "   abcd  "},
		{"abcd", 10, "   abcd   "},
		{"abcde", 6, "abcde "},
		{"abcde", 7, " abcde "},
		{"abcde", 8, " abcde  "},
		{"abcde", 9, "  abcde  "},
		{"abcde", 10, "  abcde   "},
		{"abcde", 11, "   abcde   "},
		{"abcde", 12, "   abcde    "},
		{"abcdef", 7, " abcdef"},
		{"abcdef", 8, " abcdef "},
		{"abcdef", 9, "  abcdef "},
		{"abcdef", 10, "  abcdef  "},
		{"abcdef", 11, "   abcdef  "},
		{"abcdef", 12, "   abcdef   "},
	}
	for _, c := range cases {
		if got := Center(c.s, c.width); got != c.want {
			t.Errorf("Center(%q, %d) = %q, want %q", c.s, c.width, got, c.want)
		}
	}
	if Center("toolong", 4) != "toolong" {
		t.Error("Center should return input when >= width")
	}
}

func TestLJust(t *testing.T) {
	if got := LJust("ab", 5); got != "ab   " {
		t.Errorf("LJust = %q", got)
	}
	if got := LJust("abcde", 3); got != "abcde" {
		t.Errorf("LJust short = %q", got)
	}
}

func TestSlice(t *testing.T) {
	s := "abcdef"
	cases := []struct {
		start, end int
		want       string
	}{
		{0, 3, "abc"},
		{2, 4, "cd"},
		{3, 99, "def"},
		{4, 2, ""},
		{-5, 3, "abc"},
		{99, 100, ""},
		{-1, -1, ""},
	}
	for _, c := range cases {
		if got := Slice(s, c.start, c.end); got != c.want {
			t.Errorf("Slice(%q, %d, %d) = %q, want %q", s, c.start, c.end, got, c.want)
		}
	}
	if got := Slice("héllo", 1, 3); got != "él" {
		t.Errorf("Slice unicode = %q, want %q", got, "él")
	}
}

func TestCount(t *testing.T) {
	if Count("héllo") != 5 {
		t.Errorf("Count = %d", Count("héllo"))
	}
}

func TestMoney(t *testing.T) {
	cases := []struct {
		v    float64
		want string
	}{
		{0, "0,00"},
		{1234.5, "1.234,50"},
		{1000000, "1.000.000,00"},
		{12.345, "12,35"},
		{-1234.5, "-1.234,50"},
		{0.05, "0,05"},
		{999999.99, "999.999,99"},
	}
	for _, c := range cases {
		if got := Money(c.v); got != c.want {
			t.Errorf("Money(%v) = %q, want %q", c.v, got, c.want)
		}
	}
}
