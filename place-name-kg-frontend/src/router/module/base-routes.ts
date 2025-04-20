import BasicLayout from '../../layouts/BasicLayout.vue';
import Login from '../../views/login/index.vue';


export default [
    {
        path: '/',
        redirect: '/knowledge/graph'
    },
    {
        path: '/login',
        component: Login,
        meta: {title: '登录页面'},
    },
    {
        path: "/knowledge",
        component: BasicLayout,
        meta: {title: '知识图谱'},
        children: [
            {
                path: "/knowledge/graph",
                component: () => import('../../views/knowledge/graph/index.vue'),
                meta: {title: '知识图谱可视化', requireAuth: true}
            },
            {
                path: "/knowledge-list",
                component: () => import('../../views/knowledge-list/index.vue'),
                meta: {title: '知识节点管理', requireAuth: true}
            },
            {
                path: "/knowledge/inference",
                component: () => import('../../views/inference/index.vue'),
                meta: {title: '大模型推理', requireAuth: true}
            }
        ]
    },
    {
        path: '/error',
        component: BasicLayout,
        meta: {title: '错误页面'},
        children: [
            {
                path: '/error/401',
                component: () => import('../../views/error/401.vue'),
                meta: {title: '401'},
            },
            {
                path: '/error/403',
                component: () => import('../../views/error/403.vue'),
                meta: {title: '403'},
            },
            {
                path: '/error/404',
                component: () => import('../../views/error/404.vue'),
                meta: {title: '404'},
            },
            {
                path: '/error/500',
                component: () => import('../../views/error/500.vue'),
                meta: {title: '500'},
            }
        ]
    },
]
