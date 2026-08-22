<template>
  <div>
    <BButton>Button</BButton>
    <BButton variant="danger">Button</BButton>
    <BButton variant="success">Button</BButton>
    <BButton variant="outline-primary">Button</BButton>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import axios from '@/services/axios'

onMounted(() => {
  axios
    .get('/health')
    .then((response) => {
      console.log('Backend health:', response.data)
    })
    .catch((error) => {
      console.error('Axios request failed:', error)
    })
})
</script>

<style lang="scss" scoped></style>
