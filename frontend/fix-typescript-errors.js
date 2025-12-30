#!/usr/bin/env node

/**
 * TypeScript Strict Mode Error Fix Script
 * This script automatically fixes common TypeScript strict mode errors
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

const sourceDir = './src';

// Common fixes
const fixes = [
  // Remove unused React imports
  {
    pattern: /^import React from 'react';\n/gm,
    replacement: '',
    description: 'Remove unused React imports'
  },
  
  // Fix environment variable access
  {
    pattern: /process\.env\.([A-Z_]+)/g,
    replacement: "process.env['$1']",
    description: 'Fix environment variable access'
  },
  
  // Remove unused imports (specific patterns)
  {
    pattern: /^\s*([a-zA-Z_$][a-zA-Z0-9_$]*),?\s*$/gm,
    replacement: '',
    description: 'Remove empty import lines'
  }
];

// Unused import patterns to fix
const unusedImportFixes = [
  // Match unused imports from lines like: import { UnusedThing, UsedThing } from 'module';
  {
    file: 'src/api/documents.ts',
    imports: ['DocumentFilter', 'DocumentListParams']
  },
  {
    file: 'src/services/documentService.ts',
    imports: ['DocumentFilter']
  },
  {
    file: 'src/store/documents.ts',
    imports: ['PaginationParams']
  },
  {
    file: 'src/services/apiConfig.ts',
    imports: ['EnvironmentConfig']
  },
  {
    file: 'src/services/httpClient.ts',
    imports: ['apiConfig']
  },
  {
    file: 'src/stores/documents.ts',
    imports: ['PaginationParams']
  }
];

// Environment variable fixes
const envVarFixes = [
  'src/components/common/ErrorBoundary.tsx',
  'src/pages/LoginPage.tsx',
  'src/providers/QueryProvider.tsx',
  'src/router/hooks.ts'
];

function fixFile(filePath, content) {
  let modified = content;
  let hasChanges = false;
  
  // Apply general fixes
  fixes.forEach(fix => {
    const newContent = modified.replace(fix.pattern, fix.replacement);
    if (newContent !== modified) {
      console.log(`✓ Applied: ${fix.description} in ${filePath}`);
      modified = newContent;
      hasChanges = true;
    }
  });
  
  // Fix specific unused imports
  unusedImportFixes.forEach(fix => {
    if (filePath.endsWith(fix.file)) {
      fix.imports.forEach(unusedImport => {
        // Remove from import lists
        const importRegex = new RegExp(`(import\\s*\\{[^}]*),\\s*${unusedImport}([^}]*\\})`, 'g');
        const newContent = modified.replace(importRegex, '$1$2');
        
        if (newContent !== modified) {
          console.log(`✓ Removed unused import: ${unusedImport} from ${filePath}`);
          modified = newContent;
          hasChanges = true;
        }
        
        // Also try removing it from the beginning
        const importRegex2 = new RegExp(`(import\\s*\\{)\\s*${unusedImport},\\s*([^}]*\\})`, 'g');
        const newContent2 = modified.replace(importRegex2, '$1$2');
        
        if (newContent2 !== modified) {
          console.log(`✓ Removed unused import: ${unusedImport} from ${filePath}`);
          modified = newContent2;
          hasChanges = true;
        }
      });
    }
  });
  
  return { content: modified, hasChanges };
}

async function main() {
  try {
    console.log('🔧 Starting TypeScript strict mode error fixes...\n');
    
    // Find all TypeScript and TSX files
    const files = glob.sync(`${sourceDir}/**/*.{ts,tsx}`, {
      ignore: ['**/*.d.ts', '**/node_modules/**']
    });
    
    console.log(`Found ${files.length} files to process\n`);
    
    let totalFixed = 0;
    
    for (const file of files) {
      try {
        const content = fs.readFileSync(file, 'utf8');
        const result = fixFile(file, content);
        
        if (result.hasChanges) {
          fs.writeFileSync(file, result.content, 'utf8');
          totalFixed++;
          console.log(`📝 Updated: ${file}`);
        }
      } catch (error) {
        console.error(`❌ Error processing ${file}:`, error.message);
      }
    }
    
    console.log(`\n✅ Completed! Fixed ${totalFixed} files.`);
    console.log('\n🔍 Run "npm run build" to check remaining errors.');
    
  } catch (error) {
    console.error('❌ Script failed:', error);
    process.exit(1);
  }
}

main();