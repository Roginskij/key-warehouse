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

/** Admin rights the superadmin can give. Keep in sync with backend AdminPerm. */
export const PERMS = [
  'users.view',
  'users.manage',
  'workshops.view',
  'catalog.view',
  'catalog.edit',
  'catalog.moderate',
  'catalog.import',
  'catalog.attributes',
] as const
