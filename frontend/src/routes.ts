/** The six dashboard pages, in the original user-journey order. */
export const PAGES = [
  { path: '/profile', label: '01 Profile' },
  { path: '/appearance', label: '02 Appearance' },
  { path: '/avatar', label: '03 Avatar' },
  { path: '/recommendations', label: '04 Recommendations' },
  { path: '/complete-look', label: '05 Complete Look' },
  { path: '/final-look', label: '06 Final Look' },
] as const

export type PagePath = (typeof PAGES)[number]['path']
