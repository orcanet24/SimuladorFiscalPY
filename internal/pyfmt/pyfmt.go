package pyfmt

import (
	"errors"
	"fmt"
	"math"
	"regexp"
	"strconv"
	"strings"
	"unicode"
)

var floatRe = regexp.MustCompile(`^[+-]?([0-9][0-9_]*(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$`)
var floatSpecialRe = regexp.MustCompile(`(?i)^[+-]?(nan|inf|infinity)$`)
var intRe = regexp.MustCompile(`^[+-]?[0-9]([0-9_]*[0-9])?$`)

func pyFloatError(s string) error {
	return fmt.Errorf("could not convert string to float: '%s'", s)
}

func pyIntError(s string) error {
	return fmt.Errorf("invalid literal for int() with base 10: '%s'", s)
}

func Float(s string) (float64, error) {
	t := strings.TrimSpace(s)
	if !floatRe.MatchString(t) && !floatSpecialRe.MatchString(t) {
		return 0, pyFloatError(s)
	}
	v, err := strconv.ParseFloat(t, 64)
	if err != nil {
		if errors.Is(err, strconv.ErrRange) {
			return v, nil
		}
		return 0, pyFloatError(s)
	}
	return v, nil
}

func Int(s string) (int, error) {
	t := strings.TrimSpace(s)
	if intRe.MatchString(t) {
		clean := strings.ReplaceAll(t, "_", "")
		if n, err := strconv.Atoi(clean); err == nil {
			return n, nil
		}
	}
	return 0, pyIntError(s)
}

func PyRound(x float64, ndigits int) float64 {
	if math.IsNaN(x) || math.IsInf(x, 0) {
		return x
	}
	if ndigits < 0 {
		ndigits = 0
	}
	s := strconv.FormatFloat(x, 'f', ndigits, 64)
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return x
	}
	return v
}

func PyIsDigit(r rune) bool {
	if unicode.IsDigit(r) {
		return true
	}
	switch r {
	case '\u00b2', '\u00b3', '\u00b9', '\u2070',
		'\u2074', '\u2075', '\u2076', '\u2077', '\u2078', '\u2079':
		return true
	}
	if r >= '\u2080' && r <= '\u2089' {
		return true
	}
	return false
}
