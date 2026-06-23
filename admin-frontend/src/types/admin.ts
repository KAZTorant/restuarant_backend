export interface AdminUser {
  id: number
  username: string
  full_name: string
  is_superuser: boolean
  restaurant?: { id: number; name: string } | null
}

export interface ModelPermissions {
  view: boolean
  add: boolean
  change: boolean
  delete: boolean
}

export interface NavModel {
  app_label: string
  model_name: string
  name: string
  singular_name: string
  permissions: ModelPermissions
  has_custom_list: boolean
  has_custom_form: boolean
}

export interface NavApp {
  app_label: string
  name: string
  models: NavModel[]
  order: number
}

export interface Navigation {
  user: AdminUser
  apps: NavApp[]
  site: { title: string; header: string }
}

export interface ListColumn {
  name: string
  label: string
  type: string
  sortable: boolean
}

export interface ListFilter {
  name: string
  type: string
  label: string
}

export interface ListAction {
  name: string
  label: string
}

export interface ModelMeta {
  app_label: string
  model_name: string
  verbose_name: string
  verbose_name_plural: string
  list: {
    columns: ListColumn[]
    list_filter: ListFilter[]
    search_fields: string[]
    date_hierarchy: string | null
    list_per_page: number
    ordering: string[]
    actions: ListAction[]
  }
  permissions: ModelPermissions
  has_custom_list: boolean
}

export interface FieldSchema {
  name: string
  label: string
  type: string
  required: boolean
  help_text: string
  choices: { value: string; label: string }[]
  related_model: { app_label: string; model_name: string } | null
  widget?: string
}

export interface FormSchema {
  fields: FieldSchema[]
  fieldsets: { title: string; classes: string[]; fields: string[] }[]
  inlines: unknown[]
  filter_horizontal: string[]
  readonly_fields: string[]
}

export interface ListResponse {
  count: number
  num_pages: number
  page: number
  page_size: number
  results: Record<string, unknown>[]
}

export interface DetailResponse {
  object: Record<string, unknown>
  schema: FormSchema
  permissions: { change: boolean; delete: boolean }
}
