import axios from 'axios'
import type { TripRequest, TripPlan } from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:7000',
  timeout: 600000, // LLM 生成可能耗时,这里给 10 分钟超时
})

export async function planTrip(req: TripRequest): Promise<TripPlan> {
  const resp = await api.post<TripPlan>('/api/trip/plan', req)
  return resp.data
}

/**
 * 异步模式：发起请求后立即返回 task_id
 */
export async function planTripAsync(req: TripRequest): Promise<string> {
  const resp = await api.post<{ task_id: string }>('/api/trip/plan', req)
  return resp.data.task_id
}

export interface ProgressCallback {
  (stage: string, progress: number, status: string): void
}

export interface CompleteCallback {
  (result: TripPlan): void
}

export interface ErrorCallback {
  (error: string): void
}

/**
 * 通过 SSE 接收实时进度
 */
export function planTripStream(
  taskId: string,
  onProgress: ProgressCallback,
  onComplete: CompleteCallback,
  onError: ErrorCallback
) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7000'
  const url = `${baseURL}/api/trip/plan/${taskId}/stream`
  const eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onProgress(data.stage || '', data.progress || 0, data.status || '')

      if (data.status === 'done' && data.result) {
        eventSource.close()
        onComplete(data.result)
      } else if (data.status === 'error') {
        eventSource.close()
        onError(data.error || '未知错误')
      }
    } catch (e) {
      console.error('[planTripStream] 解析 SSE 数据失败', e)
    }
  }

  eventSource.onerror = () => {
    eventSource.close()
    onError('SSE 连接失败，请重试')
  }

  // 返回关闭函数
  return () => eventSource.close()
}

export async function healthCheck(): Promise<string> {
  const resp = await api.get<{ status: string }>('/health')
  return resp.data.status
}
