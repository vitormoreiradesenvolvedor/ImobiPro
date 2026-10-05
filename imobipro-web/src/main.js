import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { iniciarTema } from '@/composables/useTema'
import './assets/style.css'
import router from './router'
import { useAuthStore } from './stores/auth'

iniciarTema()

const app = createApp(App)
app.use(createPinia())

// Antes de montar, tenta recuperar a sessão pelo cookie de refresh: um F5 não
// pode derrubar o corretor para a tela de login.
const auth = useAuthStore()
await auth.restaurarSessao()

app.use(router)
app.mount('#app')
