package orderedmap

import (
	"bytes"
	"encoding/json"
	"fmt"
)

type Map[K comparable, V any] struct {
	keys []K
	data map[K]V
}

func New[K comparable, V any]() *Map[K, V] {
	return &Map[K, V]{data: make(map[K]V)}
}

func (m *Map[K, V]) Get(k K) (V, bool) {
	v, ok := m.data[k]
	return v, ok
}

func (m *Map[K, V]) GetOr(k K, def V) V {
	if v, ok := m.data[k]; ok {
		return v
	}
	return def
}

func (m *Map[K, V]) Set(k K, v V) {
	if m.data == nil {
		m.data = make(map[K]V)
	}
	if _, ok := m.data[k]; !ok {
		m.keys = append(m.keys, k)
	}
	m.data[k] = v
}

func (m *Map[K, V]) Delete(k K) {
	if _, ok := m.data[k]; !ok {
		return
	}
	delete(m.data, k)
	for i, kk := range m.keys {
		if kk == k {
			m.keys = append(m.keys[:i], m.keys[i+1:]...)
			break
		}
	}
}

func (m *Map[K, V]) Keys() []K {
	return m.keys
}

func (m *Map[K, V]) Len() int {
	return len(m.keys)
}

func (m *Map[K, V]) Clear() {
	m.keys = nil
	m.data = make(map[K]V)
}

func (m *Map[K, V]) Clone() *Map[K, V] {
	c := New[K, V]()
	for _, k := range m.keys {
		c.Set(k, m.data[k])
	}
	return c
}

func (m *Map[K, V]) MarshalJSON() ([]byte, error) {
	var buf bytes.Buffer
	buf.WriteByte('{')
	for i, k := range m.keys {
		if i > 0 {
			buf.WriteByte(',')
		}
		kb, err := json.Marshal(k)
		if err != nil {
			return nil, err
		}
		buf.Write(kb)
		buf.WriteByte(':')
		vb, err := json.Marshal(m.data[k])
		if err != nil {
			return nil, err
		}
		buf.Write(vb)
	}
	buf.WriteByte('}')
	return buf.Bytes(), nil
}

func (m *Map[K, V]) UnmarshalJSON(b []byte) error {
	dec := json.NewDecoder(bytes.NewReader(b))
	tok, err := dec.Token()
	if err != nil {
		return err
	}
	if d, ok := tok.(json.Delim); !ok || d != '{' {
		return fmt.Errorf("orderedmap: expected {")
	}
	m.keys = nil
	m.data = make(map[K]V)
	for dec.More() {
		kt, err := dec.Token()
		if err != nil {
			return err
		}
		kb, err := json.Marshal(kt)
		if err != nil {
			return err
		}
		var k K
		if err := json.Unmarshal(kb, &k); err != nil {
			return err
		}
		var v V
		if err := dec.Decode(&v); err != nil {
			return err
		}
		m.Set(k, v)
	}
	if _, err := dec.Token(); err != nil {
		return err
	}
	return nil
}
