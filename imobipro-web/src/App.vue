<script setup>
import { RouterView } from 'vue-router'

import ConfirmHost from '@/components/base/ConfirmHost.vue'
import ToastHost from '@/components/base/ToastHost.vue'
</script>

<template>
  <RouterView />
  <ToastHost />
  <ConfirmHost />
</template>
