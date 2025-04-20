<template>
  <router-view></router-view>
</template>
<style>
@import "./styles/index.css";

#app {
  height: 100%;
}

body {
  height: 100%;
}

html {
  height: 100%;
}


::-webkit-scrollbar {
  width: 5px;
  height: 5px;
  background-color: #F5F5F5;
}

::-webkit-scrollbar-track {
  -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.3);
  border-radius: 10px;
  background-color: #F5F5F5;
}

::-webkit-scrollbar-thumb {
  border-radius: 10px;
  -webkit-box-shadow: inset 0 0 6px rgba(0, 0, 0, .3);
  background-color: #555;
  cursor: pointer;
}

pre.hljs {
  position: relative;
  padding: 10px;
  overflow: auto;
}

pre.hljs:hover .copy-code-button {
  pointer-events: all;
  transform: translateX(0px);
  opacity: 1;
}

pre.hljs .copy-code-button {
  position: absolute;
  right: 10px;
  top: 10px;
  padding: 0 4px;
  cursor: pointer;
  background-color: var(--black);
  color: var(--white);
  border: 1px solid #ccc;
  border-radius: 10px;
  transform: translateX(10px);
  pointer-events: none;
  opacity: 0;
  transition: all ease 0.3s;
  text-align: center;
}

pre.hljs .copy-code-button:hover {
  opacity: 1;
}

</style>
