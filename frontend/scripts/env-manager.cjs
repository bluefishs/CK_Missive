#!/usr/bin/env node

/**
 * 環境變數管理工具
 * 用於統一管理和驗證環境變數配置
 */

const fs = require('fs');
const path = require('path');

class EnvManager {
  constructor() {
    this.rootDir = path.resolve(__dirname, '..');
    this.envFiles = {
      base: '.env',
      development: '.env.development',
      production: '.env.production',
      local: '.env.local'
    };
  }

  /**
   * 讀取環境變數檔案
   */
  readEnvFile(filename) {
    const filePath = path.join(this.rootDir, filename);
    if (!fs.existsSync(filePath)) {
      return {};
    }

    const content = fs.readFileSync(filePath, 'utf-8');
    const env = {};

    content.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=');
        if (key && valueParts.length > 0) {
          env[key.trim()] = valueParts.join('=').trim();
        }
      }
    });

    return env;
  }

  /**
   * 獲取所有環境變數
   */
  getAllEnvVars() {
    const allEnvs = {};

    // 按優先級順序載入
    Object.values(this.envFiles).forEach(filename => {
      const env = this.readEnvFile(filename);
      Object.assign(allEnvs, env);
    });

    return allEnvs;
  }

  /**
   * 驗證關鍵環境變數
   */
  validateEnvVars() {
    const envs = this.getAllEnvVars();
    const required = [
      'VITE_API_BASE_URL',
      'VITE_APP_TITLE',
      'VITE_GOOGLE_CLIENT_ID'
    ];

    const missing = required.filter(key => !envs[key]);
    const warnings = [];

    // 檢查是否有硬編碼的localhost URLs
    Object.entries(envs).forEach(([key, value]) => {
      if (value.includes('localhost:8002')) {
        warnings.push(`⚠️  ${key}包含硬編碼的8002端口: ${value}`);
      }
      if (value.includes('localhost') && key.includes('PROD')) {
        warnings.push(`⚠️  生產環境變數${key}包含localhost: ${value}`);
      }
    });

    return { missing, warnings, valid: missing.length === 0 };
  }

  /**
   * 生成環境變數報告
   */
  generateReport() {
    console.log('🔍 環境變數配置報告');
    console.log('='.repeat(50));

    const envs = this.getAllEnvVars();
    const validation = this.validateEnvVars();

    console.log('\n📋 當前配置:');
    Object.entries(envs)
      .filter(([key]) => key.startsWith('VITE_'))
      .forEach(([key, value]) => {
        console.log(`  ${key} = ${value}`);
      });

    if (validation.missing.length > 0) {
      console.log('\n❌ 缺少的必要變數:');
      validation.missing.forEach(key => console.log(`  - ${key}`));
    }

    if (validation.warnings.length > 0) {
      console.log('\n⚠️  警告:');
      validation.warnings.forEach(warning => console.log(`  ${warning}`));
    }

    if (validation.valid && validation.warnings.length === 0) {
      console.log('\n✅ 所有環境變數配置正確！');
    }

    return validation;
  }

  /**
   * 修復常見問題
   */
  fixCommonIssues() {
    console.log('🔧 正在修復常見的環境變數問題...');

    // 備份現有檔案
    Object.values(this.envFiles).forEach(filename => {
      const filePath = path.join(this.rootDir, filename);
      if (fs.existsSync(filePath)) {
        const backupPath = `${filePath}.backup.${Date.now()}`;
        fs.copyFileSync(filePath, backupPath);
        console.log(`  📦 已備份 ${filename} 到 ${path.basename(backupPath)}`);
      }
    });

    // 移除有問題的環境變數檔案中的8002硬編碼
    ['.env.production', '.env.development'].forEach(filename => {
      const filePath = path.join(this.rootDir, filename);
      if (fs.existsSync(filePath)) {
        let content = fs.readFileSync(filePath, 'utf-8');
        const original = content;

        // 修復8002端口
        content = content.replace(/localhost:8002/g, '/api');
        content = content.replace(/http:\/\/[^\/]+:8002/g, '/api');

        if (content !== original) {
          fs.writeFileSync(filePath, content);
          console.log(`  🔧 已修復 ${filename} 中的8002端口問題`);
        }
      }
    });
  }
}

// CLI 執行
if (require.main === module) {
  const manager = new EnvManager();
  const command = process.argv[2];

  switch (command) {
    case 'validate':
      manager.generateReport();
      break;
    case 'fix':
      manager.fixCommonIssues();
      manager.generateReport();
      break;
    default:
      console.log('環境變數管理工具');
      console.log('用法:');
      console.log('  node scripts/env-manager.js validate  # 檢查配置');
      console.log('  node scripts/env-manager.js fix       # 修復常見問題');
  }
}

module.exports = EnvManager;