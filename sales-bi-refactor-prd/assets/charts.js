// assets/charts.js
(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  function grad(from, to) {
    return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: from }, { offset: 1, color: to }
    ]);
  }

  var stack = echarts.init(document.getElementById('chart-stack'), null, { renderer: 'svg' });
  var days = ['09-02', '09-03', '09-04', '09-05', '09-06', '09-07', '09-08'];
  stack.setOption({
    animation: false,
    tooltip: { trigger: 'axis', appendToBody: true, backgroundColor: 'rgba(13,23,48,0.9)', borderColor: rule, textStyle: { color: ink } },
    legend: {
      data: ['订单量', '销售额'], textStyle: { color: muted }, top: 0
    },
    grid: { left: 50, right: 50, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: days, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted } },
    yAxis: [
      { type: 'value', name: '订单量', nameTextStyle: { color: muted }, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      { type: 'value', name: '销售额', nameTextStyle: { color: muted }, axisLine: { lineStyle: { color: rule } }, axisLabel: { color: muted }, splitLine: { show: false } }
    ],
    series: [
      {
        name: '订单量', type: 'bar', barWidth: 22,
        itemStyle: { borderRadius: [6, 6, 0, 0], color: grad(accent, accent2) },
        data: [1560, 1712, 1648, 1830, 1755, 1904, 1798]
      },
      {
        name: '销售额', type: 'line', yAxisIndex: 1, smooth: true,
        itemStyle: { color: accent2 },
        lineStyle: { color: accent2, width: 3 },
        areaStyle: { color: grad(accent2 + '55', 'rgba(0,0,0,0)') },
        data: [6.8, 7.4, 7.1, 8.0, 7.6, 8.3, 7.9]
      }
    ]
  });

  window.addEventListener('resize', function() { stack.resize(); });
})();