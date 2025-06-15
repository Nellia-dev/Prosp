import { MigrationInterface, QueryRunner, TableColumn } from 'typeorm';

export class AddUserSearchQueryToBusinessContext1749268814244 implements MigrationInterface {
  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.addColumn(
      'business_context',
      new TableColumn({
        name: 'user_search_query',
        type: 'varchar',
        isNullable: true,
      }),
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.dropColumn('business_context', 'user_search_query');
  }
}
