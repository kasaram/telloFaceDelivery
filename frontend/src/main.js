import Vue from 'vue'
import VueResource from 'vue-resource'

import ElementUI from 'element-ui'

import App from './App.vue'

Vue.config.productionTip = false

Vue.use(ElementUI)
Vue.use(VueResource)

new Vue({
  render: h => h(App)
}).$mount('#app')
