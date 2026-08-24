<!-- App.vue -->
<template>
  <div>
    <img src="/django_design/django-app-icon-dark.svg" height="40px" alt="Django logo">
     <button
      class="btn btn-primary"
      @click="checkHealth"
    >Check Health
    </button>
  </div>
  <BApp>
    <!-- Your application content -->
    <router-view />
  </BApp>
</template>

<script setup lang="ts">
import axios from './services/axios';
import { BApp } from 'bootstrap-vue-next'
const checkHealth = ()=>{
axios.get('/health')
}
</script>
