const BASE_URL = "https://weather-api.example.com";

function getThreadId() {
  const key = "threadId";
  const cached = wx.getStorageSync(key);
  if (cached) return cached;
  const id = `wx-${Date.now()}`;
  wx.setStorageSync(key, id);
  return id;
}

Page({
  data: {
    message: "外面的天气怎么样？",
    loading: false,
    locating: false,
    latitude: null,
    longitude: null,
    locationText: "",
    result: null
  },

  onMessageChange(e) {
    this.setData({ message: e.detail.value });
  },

  useCurrentLocation() {
    this.setData({ locating: true });
    wx.getLocation({
      type: "wgs84",
      success: (res) => {
        this.setData({
          latitude: res.latitude,
          longitude: res.longitude,
          locationText: `已获取坐标：${res.latitude.toFixed(4)}, ${res.longitude.toFixed(4)}`
        });
      },
      fail: () => {
        wx.showToast({ title: "定位失败，请手动输入城市", icon: "none" });
      },
      complete: () => {
        this.setData({ locating: false });
      }
    });
  },

  queryWeather() {
    const { message, latitude, longitude } = this.data;
    if (!message || !message.trim()) {
      wx.showToast({ title: "请输入查询内容", icon: "none" });
      return;
    }

    this.setData({ loading: true });
    wx.request({
      url: `${BASE_URL}/v1/chat`,
      method: "POST",
      header: { "content-type": "application/json" },
      data: {
        message: message.trim(),
        thread_id: getThreadId(),
        latitude,
        longitude
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          this.setData({ result: res.data });
          return;
        }
        wx.showToast({ title: "查询失败，请稍后再试", icon: "none" });
      },
      fail: () => {
        wx.showToast({ title: "网络异常，请检查域名与 HTTPS 配置", icon: "none" });
      },
      complete: () => {
        this.setData({ loading: false });
      }
    });
  }
});
