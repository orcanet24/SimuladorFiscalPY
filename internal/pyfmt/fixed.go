package pyfmt

import (
	"fmt"
	"math"
	"strconv"
	"strings"
)

func Fixed(v float64, width, prec int) string {
	var s string
	switch {
	case math.IsNaN(v):
		s = "nan"
	case math.IsInf(v, 1):
		s = "inf"
	case math.IsInf(v, -1):
		s = "-inf"
	default:
		return fmt.Sprintf("%*.*f", width, prec, v)
	}
	if len(s) < width {
		s = strings.Repeat(" ", width-len(s)) + s
	}
	return s
}

func FormatFloatPython(v float64, format byte, prec int) string {
	if math.IsNaN(v) || math.IsInf(v, 0) {
		return FormatSpecialPython(v)
	}
	return strconv.FormatFloat(v, format, prec, 64)
}

func FormatSpecialPython(v float64) string {
	switch {
	case math.IsNaN(v):
		return "nan"
	case math.IsInf(v, 1):
		return "inf"
	default:
		return "-inf"
	}
}

func F2(v float64) string {
	return FormatFloatPython(v, 'f', 2)
}

func F3(v float64) string {
	return FormatFloatPython(v, 'f', 3)
}
