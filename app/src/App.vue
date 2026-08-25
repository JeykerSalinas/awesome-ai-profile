<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <UApp :toaster="{ position: 'top-right' }">
    <RouterView />
  </UApp>
</template>
