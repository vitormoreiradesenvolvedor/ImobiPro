<script setup>
defineProps({
  titulo: { type: String, default: '' },
  subtitulo: { type: String, default: '' },
})
</script>

<template>
  <section class="cartao p-5">
    <header v-if="titulo || $slots.acoes" class="mb-4 flex items-start justify-between gap-4">
      <div>
        <h2 v-if="titulo" class="text-base font-semibold text-slate-900">{{ titulo }}</h2>
        <p v-if="subtitulo" class="text-sm text-slate-500">{{ subtitulo }}</p>
      </div>
      <slot name="acoes" />
    </header>
    <slot />
  </section>
</template>
