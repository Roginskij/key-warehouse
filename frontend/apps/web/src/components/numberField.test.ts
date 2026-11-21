import { UIField } from '@kv/ui'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

async function typeInto(props: Record<string, unknown>, text: string) {
  const w = mount(UIField, { props: { label: 'x', modelValue: '', ...props } })
  await w.find('input').setValue(text)
  const emitted = w.emitted('update:modelValue') ?? []
  return { model: emitted.at(-1)?.[0], shown: (w.find('input').element as HTMLInputElement).value }
}

describe('number fields', () => {
  it('a price takes only a number with two decimals', async () => {
    const r = await typeInto({ inputmode: 'decimal', decimals: 2 }, 'від 1a2,345.6 грн')
    expect(r).toEqual({ model: '12,34', shown: '12,34' })
  })

  it('a quantity takes only digits', async () => {
    expect((await typeInto({ inputmode: 'numeric' }, '3 шт.')).model).toBe('3')
  })

  it('a text field is left alone', async () => {
    expect((await typeInto({}, 'HU-66 Silca')).model).toBe('HU-66 Silca')
  })
})
