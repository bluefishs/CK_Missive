declare module 'swagger-ui-react' {
  import { ComponentType } from 'react';

  interface SwaggerUIProps {
    url?: string;
    spec?: object | null;
    docExpansion?: 'list' | 'full' | 'none';
    defaultModelsExpandDepth?: number;
    displayOperationId?: boolean;
    filter?: boolean | string;
    maxDisplayedTags?: number;
    showExtensions?: boolean;
    showCommonExtensions?: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    requestInterceptor?: (req: any) => any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    responseInterceptor?: (res: any) => any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onComplete?: (system: any) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    plugins?: any[];
    supportedSubmitMethods?: string[];
    tryItOutEnabled?: boolean;
    validatorUrl?: string | null;
    withCredentials?: boolean;
  }

  const SwaggerUI: ComponentType<SwaggerUIProps>;
  export default SwaggerUI;
}
