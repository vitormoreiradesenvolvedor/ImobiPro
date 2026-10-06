<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="grid min-h-screen place-items-center px-6 text-center">
    <div>
      <p class="text-6xl font-black text-marca">404</p>
      <h1 class="mt-4 text-xl font-bold text-slate-900">Página não encontrada</h1>
      <p class="mt-2 text-sm text-slate-500">O endereço acessado não existe no ImobiPro.</p>
      <RouterLink
        :to="{ name: 'dashboard' }"
        class="mt-6 inline-block rounded-lg bg-marca px-4 py-2.5 text-sm font-semibold text-white"
      >
        Voltar ao dashboard
      </RouterLink>
    </div>
  </div>
</template>
