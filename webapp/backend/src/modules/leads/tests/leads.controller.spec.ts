import { Test, TestingModule } from '@nestjs/testing';
import { LeadsController } from '../leads.controller';
import { LeadsService } from '../leads.service';
import { UserId } from '../../auth/user-id.decorator'; // Assuming this path is correct
import { BadRequestException } from '@nestjs/common';
import { LeadFilters, LeadData } from '@/shared/types/nellia.types'; // Adjust path as needed

// Mock data
const mockUserId = 'user-test-id';
const mockLeadId = 'lead-test-id';

const mockLeadData: LeadData = {
  id: mockLeadId,
  company_name: 'TestCo',
  website: 'test.co',
  relevance_score: 0.7,
  roi_potential_score: 0.6,
  qualification_tier: 'HIGH_POTENTIAL' as any, // Cast for simplicity if enums are not directly used in DTOs
  company_sector: 'Tech',
  processing_stage: 'PROSPECTING' as any,
  status: 'NEW' as any,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  // Add other fields from LeadData as needed
};

describe('LeadsController', () => {
  let controller: LeadsController;
  let service: LeadsService;

  // Mock LeadsService
  const mockLeadsService = {
    markAsSeen: jest.fn(),
    findAll: jest.fn(),
    // Add other methods used by the controller if necessary for other tests
    findOne: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    updateStage: jest.fn(),
    remove: jest.fn(),
    getLeadsStats: jest.fn(),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [LeadsController],
      providers: [
        {
          provide: LeadsService,
          useValue: mockLeadsService,
        },
      ],
    })
    // Mocking the UserId decorator's behavior for tests
    // This approach depends on how UserId decorator is implemented (e.g., ExecutionContext)
    // For simplicity, we can directly mock its resolved value if it's simple enough,
    // or more robustly, mock parts of the execution context if needed by the decorator.
    // However, NestJS testing often relies on overriding guards/decorators at module level for e2e,
    // for unit tests, it's often about ensuring the method is called with params it would receive.
    // Here, we'll assume the decorator correctly extracts the ID and passes it.
    .compile();

    controller = module.get<LeadsController>(LeadsController);
    service = module.get<LeadsService>(LeadsService);

    // Reset mocks before each test
    mockLeadsService.markAsSeen.mockClear().mockResolvedValue(undefined);
    mockLeadsService.findAll.mockClear().mockResolvedValue({ data: [mockLeadData], total: 1 });
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('markLeadAsSeen', () => {
    it('should call leadsService.markAsSeen with correct userId and leadId', async () => {
      await controller.markLeadAsSeen(mockLeadId, mockUserId);
      expect(service.markAsSeen).toHaveBeenCalledWith(mockUserId, mockLeadId);
    });

    it('should throw BadRequestException if userId is missing', async () => {
      // The decorator or guard should ideally prevent this, but controller has a check.
      await expect(controller.markLeadAsSeen(mockLeadId, null)).rejects.toThrow(BadRequestException);
      expect(service.markAsSeen).not.toHaveBeenCalled();
    });

    it('should throw BadRequestException if leadId is missing (controller check)', async () => {
        // This check is also in the controller for robustness, though typically @Param handles it
        await expect(controller.markLeadAsSeen(null, mockUserId)).rejects.toThrow(BadRequestException);
        expect(service.markAsSeen).not.toHaveBeenCalled();
    });
  });

  describe('findAll', () => {
    const mockFilters: LeadFilters = { limit: 10, offset: 0 };

    it('should call leadsService.findAll with userId and filters', async () => {
      const result = await controller.findAll(mockFilters, mockUserId);
      expect(service.findAll).toHaveBeenCalledWith(mockUserId, mockFilters);
      expect(result).toEqual({ data: [mockLeadData], total: 1 });
    });

    it('should throw BadRequestException if userId is missing when calling findAll', async () => {
      await expect(controller.findAll(mockFilters, null)).rejects.toThrow(BadRequestException);
      expect(service.findAll).not.toHaveBeenCalled();
    });
  });
});
