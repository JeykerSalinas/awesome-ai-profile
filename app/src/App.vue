<!-- App.vue -->
<template>
  <div>
    <img src="/django_design/django-app-icon-dark.svg" height="40px" alt="Django logo">
  </div>
  <BApp>
    <!-- Your application content -->
    <router-view />
  </BApp>
</template>

<script setup lang="ts">
import {BApp} from 'bootstrap-vue-next'
</script>
