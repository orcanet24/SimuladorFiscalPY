package pyfmt

import (
	"math"
	"strconv"
	"strings"
	"unicode/utf8"
)

func Count(s string) int {
	return utf8.RuneCountInString(s)
}

func Slice(s string, start, end int) string {
	r := []rune(s)
	n := len(r)
	if start < 0 {
		start = 0
	}
	if start > n {
		start = n
	}
	if end < 0 {
		end = 0
	}
	if end > n {
		end = n
	}
	if end < start {
		end = start
	}
	return string(r[start:end])
}

func Center(s string, width int) string {
	n := utf8.RuneCountInString(s)
	if n >= width {
		return s
	}
	marg := width - n
	left := marg / 2
	if marg%2 == 1 && n%2 == 0 {
		left++
	}
	right := marg - left
	return strings.Repeat(" ", left) + s + strings.Repeat(" ", right)
}

func LJust(s string, width int) string {
	n := utf8.RuneCountInString(s)
	if n >= width {
		return s
	}
	return s + strings.Repeat(" ", width-n)
}

func Money(v float64) string {
	switch {
	case math.IsNaN(v):
		return "nan"
	case math.IsInf(v, 1):
		return "inf"
	case math.IsInf(v, -1):
		return "-inf"
	}
	s := strconv.FormatFloat(v, 'f', 2, 64)
	neg := strings.HasPrefix(s, "-")
	if neg {
		s = s[1:]
	}
	intPart := s
	frac := ""
	if dot := strings.IndexByte(s, '.'); dot >= 0 {
		intPart, frac = s[:dot], s[dot+1:]
	}
	var b strings.Builder
	b.Grow(len(intPart) + len(intPart)/3 + 1 + len(frac))
	if neg {
		b.WriteByte('-')
	}
	for i, c := range []byte(intPart) {
		if i > 0 && (len(intPart)-i)%3 == 0 {
			b.WriteByte('.')
		}
		b.WriteByte(c)
	}
	b.WriteByte(',')
	b.WriteString(frac)
	return b.String()
}
