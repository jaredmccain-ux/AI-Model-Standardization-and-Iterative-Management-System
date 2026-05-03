const STORAGE_KEY = 'ai_image_recognition_current_project'

export const getCurrentProject = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || !parsed.id || !parsed.name) return null
    return parsed
  } catch {
    return null
  }
}

export const setCurrentProject = (project) => {
  if (!project?.id || !project?.name) return
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    id: project.id,
    name: project.name
  }))
}

export const clearCurrentProject = () => {
  localStorage.removeItem(STORAGE_KEY)
}
