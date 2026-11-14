import { useQuery } from '@tanstack/vue-query'
import { call, client } from '@/lib/api'

export const KINDS = ['blank', 'car_key', 'remote', 'transponder', 'cylinder', 'key_shell', 'battery', 'machine', 'programmer', 'other'] as const

export function useBrands() {
  return useQuery({
    queryKey: ['admin-brands'],
    queryFn: () => call(client.GET('/api/v1/admin/catalog/brands')),
    staleTime: 60_000,
  })
}
