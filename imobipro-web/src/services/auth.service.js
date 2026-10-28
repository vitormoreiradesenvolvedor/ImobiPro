import http from './http'

export const authService = {
  login: (email, password) => http.post('/auth/login/', { email, password }),
  cadastrar: (dados) => http.post('/auth/cadastro/', dados),
  refresh: () => http.post('/auth/refresh/'),
  logout: () => http.post('/auth/logout/'),
  perfil: () => http.get('/auth/me/'),
  solicitarResetSenha: (email) => http.post('/auth/password-reset/', { email }),
}
