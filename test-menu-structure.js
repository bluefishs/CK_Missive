// 測試選單結構的腳本
async function testMenuStructure() {
  try {
    const response = await fetch('http://localhost:3000/api/site-management/navigation');
    const data = await response.json();

    console.log('=== 選單結構測試 ===');
    console.log(`總選單項目數: ${data.total}`);

    data.items.forEach((item, index) => {
      console.log(`\n${index + 1}. ${item.title} (${item.key})`);
      console.log(`   路徑: ${item.path || '無'}`);
      console.log(`   圖標: ${item.icon || '無'}`);

      if (item.children && item.children.length > 0) {
        console.log(`   子項目 (${item.children.length}個):`);
        item.children.forEach((child, childIndex) => {
          console.log(`     ${childIndex + 1}.${child.title} (${child.key})`);
          console.log(`        路徑: ${child.path || '無'}`);
          console.log(`        圖標: ${child.icon || '無'}`);
        });
      } else {
        console.log('   無子項目');
      }
    });

    // 檢查是否有樹狀結構
    const hasChildren = data.items.some(item => item.children && item.children.length > 0);
    console.log(`\n=== 結果 ===`);
    console.log(`是否包含樹狀結構: ${hasChildren ? '✅ 是' : '❌ 否'}`);

    if (hasChildren) {
      const parentCount = data.items.filter(item => item.children && item.children.length > 0).length;
      const totalChildren = data.items.reduce((sum, item) => sum + (item.children ? item.children.length : 0), 0);
      console.log(`父選單數量: ${parentCount}`);
      console.log(`子選單總數: ${totalChildren}`);
    }

  } catch (error) {
    console.error('測試失敗:', error);
  }
}

testMenuStructure();